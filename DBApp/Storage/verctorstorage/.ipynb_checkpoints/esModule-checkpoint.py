from elasticsearch import Elasticsearch
from elasticsearch import exceptions
from elasticsearch.helpers import bulk
from sklearn.neighbors import KDTree
import os
from ...ModelServer.EmbeddingServer.utils import embedding_encode
from ...ModelServer.ReRanker.utils import rerank_pairs
import numpy as np


class ES_DB_Control():
    def __init__(self, es_url='http://localhost:19200', index_name='newtest01', username='elastic', password="=ebqAuSluLI_9oKimT5D"):
        # 创建 Elasticsearch 客户端对象，添加用户名和密码认证
        self.es = Elasticsearch(
            [es_url],
            http_auth=(username, password),  # 使用 http_auth 参数传递用户名和密码
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
        )
        self.index_name = index_name
        # 测试连接
        try:
            info = self.es.info()
            print("Connected to Elasticsearch:", info)
        except Exception as e:
            print("Failed to connect to Elasticsearch:", e)

    def create_index(self, vector_dims=1024):
        mapping = {
            "mappings": {
                "properties": {
                    "db_name": {"type": "keyword"},
                    "pagecontent": {"type": "text"},
                    "offset_start": {"type": "integer"},
                    "offset_end": {"type": "integer"},
                    "embeddingvector": {"type": "dense_vector", "dims": vector_dims},
                    "file_name": {"type": "keyword"}
                }
            }
        }
        self.es.indices.create(index=self.index_name, body=mapping, ignore=400)

    def UpChunks2DB(self, chunks):
        documents = []
        for chunk in chunks:
            document = {
                "_index": self.index_name,
                # "_type": "_doc",  # 注意：8.x 中 _type 已废弃，但兼容
                "_source": {
                    "db_name": chunk.metadata.extracted_info["DBName"],
                    "pagecontent": chunk.content,
                    "offset_start": chunk.metadata.offset_start,
                    "offset_end": chunk.metadata.offset_end,
                    "embeddingvector": chunk.metadata.embeddingVector["embedding"],
                    "file_name": chunk.metadata.extracted_info["file_name"],
                }
            }
            documents.append(document)

        # print("Documents to upload:", documents)
        # 分片上传
        num = len(documents) // 100
        for i in range(num + 1):
            try:
                result = bulk(self.es, documents[100*i: 100*i+100])
                print(f"Uploaded chunk {i+1}/{num+1}: {result}")
            except Exception as e:
                print(f"Failed to upload chunk {i+1}/{num+1}: {e}")
                raise  # 抛出异常以便调试

        # 强制刷新索引，确保数据立即可查
        try:
            self.es.indices.refresh(index=self.index_name)
            print(f"Index {self.index_name} refreshed")
        except Exception as e:
            print(f"Failed to refresh index: {e}")

    def search_by_db_doc_name(self, db_name, doc_name):
        try:
            query = {
                "bool": {
                    "must": [
                        {"term": {"db_name.keyword": db_name}},
                        {"term": {"file_name.keyword": doc_name}}
                    ]
                }
            }
            result = self.es.search(index=self.index_name, body={"query": query}, size=10000)
            doc_ids = [doc["_id"] for doc in result["hits"]["hits"]]
            docs = self.es.mget(index=self.index_name, body={"docs": [{"_id": doc_id} for doc_id in doc_ids]})
            documents = [doc['_source'] for doc in docs['docs'] if doc['found']]
            return documents
        except Exception as e:
            return []

    def delete_document_by_db_and_doc_name(self, db_name, doc_names):
        bulk_body = []
        for doc_name in doc_names:
            query = {
                "bool": {
                    "must": [
                        {"term": {"db_name.keyword": db_name}},
                        {"term": {"file_name.keyword": doc_name}}
                    ]
                }
            }
            result = self.es.search(index=self.index_name, body={"query": query}, size=10000)
            doc_ids = [doc["_id"] for doc in result["hits"]["hits"]]
            for doc_id in doc_ids:
                bulk_body.append({"delete": {"_index": self.index_name, "_id": doc_id}})
        if bulk_body:
            self.es.bulk(body=bulk_body)

    def delete_documents_by_db_name(self, db_name):
        query = {
            "query": {
                "term": {
                    "db_name.keyword": db_name
                }
            }
        }
        result = self.es.search(index=self.index_name, body=query, size=10000)
        doc_ids = [doc["_id"] for doc in result["hits"]["hits"]]
        bulk_body = [{"delete": {"_index": self.index_name, "_id": doc_id}} for doc_id in doc_ids]
        self.es.bulk(body=bulk_body)
        print(f"Deleted {len(doc_ids)} documents with db name '{db_name}'.")

    def get_unique_db_names_and_counts(self):
        query = {
            "size": 0,
            "aggs": {
                "db_name_count": {
                    "terms": {
                        "field": "db_name",
                        "size": 100,
                        "missing": "NULL"  # 处理db_name字段缺失的情况
                    }
                }
            }
        }
        try:
            result = self.es.search(
                index=self.index_name,
                body=query,
                ignore_unavailable=True
            )
            # print("\n=== Debug: Full Query Result ===")
            # print(json.dumps(result, indent=2, ensure_ascii=False))
            # print("===\n")
            # 检查索引是否存在文档
            total_docs = result.get('hits', {}).get('total', {}).get('value', 0)
            print(f"Total documents in index: {total_docs}")
            if not result or "aggregations" not in result:
                print("Warning: No aggregations in result")
                return []
            buckets = result["aggregations"]["db_name_count"].get("buckets", [])
            print(f"Found {len(buckets)} unique db_names")
            db_name_info = [
                {
                    "db_name": bucket["key"],
                    "count": bucket["doc_count"]
                } 
                for bucket in buckets
            ]
            # 检查是否有文档但db_name字段缺失
            if total_docs > 0 and len(db_name_info) == 0:
                print(f"Warning: Found {total_docs} documents but no db_name fields")
        except exceptions.NotFoundError:
            print(f"Index {self.index_name} not found")
            db_name_info = []
        except Exception as e:
            print(f"Error querying unique db_names: {str(e)}")
            db_name_info = []
        return db_name_info

    def get_unique_titles(self, db_name):
        aggregation_query = {
            "query": {
                "term": {
                    "db_name.keyword": db_name
                }
            },
            "aggs": {
                "file_name_count": {
                    "terms": {
                        "field": "file_name.keyword",
                        "size": 100
                    }
                }
            }
        }
        response = self.es.search(index=self.index_name, body=aggregation_query)
        unique_titles_buckets = response["aggregations"]["file_name_count"]["buckets"]
        unique_titles_count = len(unique_titles_buckets)
        unique_titles = [bucket['key'] for bucket in unique_titles_buckets]
        return unique_titles_count, unique_titles


class ES_DB_search:
    def __init__(self, es_url='http://localhost:19200', index_name='newtest01', username='elastic', password='=ebqAuSluLI_9oKimT5D'):
        print(f"Attempting to connect to {es_url} for ES_DB_search")
        # 使用与 ES_DB_Control 一致的配置
        self.es = Elasticsearch(
            [es_url],
            basic_auth=(username, password),  # 使用 basic_auth，与 8.x 兼容
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
            timeout=30,
            verify_certs=False  # 禁用证书验证，与 HTTP 一致
        )
        self.index_name = index_name
        # 测试连接
        try:
            info = self.es.info()
            print("Connected to Elasticsearch for ES_DB_search:", info)
        except Exception as e:
            print("Failed to connect to Elasticsearch for ES_DB_search:", e)

    # 全文搜索查询
    def full_text_search(self, db_name, query_text, n=5):
        search_query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"db_name.keyword": db_name}},
                        {"match": {"pagecontent": query_text}}
                    ]
                }
            },
            "size": n
        }
        search_results = self.es.search(index=self.index_name, body=search_query)
        documents = search_results['hits']['hits']
        return documents

    # BM25 搜索
    def bm25_search(self, db_name, query_text, n=5):
        search_query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"db_name.keyword": db_name}},
                        {"match": {
                            "pagecontent": {
                                "query": query_text,
                                "analyzer": "standard"
                            }
                        }}
                    ]
                }
            },
            "size": 100,
            "track_scores": True,
            "min_score": 0
        }
        search_results = self.es.search(index=self.index_name, body=search_query)
        documents = search_results['hits']['hits']
        bm25_results = [(doc['_source']['pagecontent'],
                        doc['_source']['db_name']) 
                        for doc in documents]
        return bm25_results[:n]
    
    def vector_search_es(self, db_name, query_vector, n=5):
        query_vector = query_vector / np.linalg.norm(query_vector)
        # knn_query = {
        #     "knn": {
        #         "field": "embeddingvector",
        #         "query_vector": query_vector.tolist(),
        #         "k": n,
        #         "num_candidates": n * 5
        #     },
        #     "query": {
        #         "bool": {
        #             "filter": [
        #                 {"term": {"db_name.keyword": db_name}},
        #                 {"exists": {"field": "embeddingvector"}}
        #             ]
        #         }
        #     }
        # }
        knn_query = {
            "knn": {
                "field": "embeddingvector",
                "query_vector": query_vector.tolist(),
                "k": n,
                "num_candidates": n * 5
            }
        }
        try:
            search_results = self.es.knn_search(index=self.index_name, body=knn_query)
            documents = search_results['hits']['hits']
            return [(doc['_source']['pagecontent'], doc['_source']['db_name']) for doc in documents]
        except Exception as e:
            print(f"Vector search failed: {str(e)}")
            # print(f"Query used: {json.dumps(knn_query, indent=2)}")
            return []

    # 重排序
    def reranker(self, query_text, nearest_pagecontents):
        df = [[query_text, content[0]] for content in nearest_pagecontents]
        reranker_scores_ = rerank_pairs(df)
        reranker_scores = [score for score in reranker_scores_]
        if isinstance(reranker_scores, float):
            reranker_scores = [reranker_scores]
        threshold = -10
        combined_data = list(zip(reranker_scores, nearest_pagecontents))
        combined_data.sort(reverse=True, key=lambda x: x[0])
        if combined_data[0][0] < threshold:
            reranker_nearest_pagecontents = []
            reranker_scores_sorted = []
        else:
            reranker_nearest_pagecontents = [x[1] for x in combined_data]
            reranker_scores_sorted = [(x[0] + 10) / 20 for x in combined_data]
        return reranker_nearest_pagecontents, reranker_scores_sorted

    # 单数据库混合搜索
    def hybrid_search(self, db_name, query_text, n):
        query_vector = embedding_encode(query_text)
        # print("Query Vector:", query_vector)
        # print("Vector Type:", type(query_vector))
        # print("Element Types:", [type(x) for x in query_vector])
        bm25_results = self.bm25_search(db_name, query_text, n)
        vector_results = self.vector_search_es(db_name, query_vector, n)
        combined_results = list(set(bm25_results + vector_results))
        reranker_nearest_pagecontents, reranker_scores_sorted = self.reranker(query_text, combined_results)
        return reranker_nearest_pagecontents[:n], reranker_scores_sorted[:n]

    # 多数据库混合搜索
    def hybrid_search_multydb(self, db_names, query_text, n):
        query_vector = embedding_encode(query_text)
        combined_results = []
        for db_name in db_names:
            bm25_results = self.bm25_search(db_name, query_text, n)
            vector_results = self.vector_search_es(db_name, query_vector, n)
            db_results = list(set(bm25_results + vector_results))
            combined_results.extend(db_results)
        
        reranker_nearest_pagecontents, reranker_scores_sorted = self.reranker(query_text, combined_results)
        if len(reranker_nearest_pagecontents) <= n:
            return (reranker_nearest_pagecontents[:len(reranker_nearest_pagecontents)], 
                    reranker_scores_sorted[:len(reranker_scores_sorted)])
        return reranker_nearest_pagecontents[:n], reranker_scores_sorted[:n]














# from elasticsearch import Elasticsearch
# from elasticsearch import exceptions
# from elasticsearch.helpers import bulk
# from sklearn.neighbors import KDTree
# # from .utils import embedding_encode, rerank_pairs
# import os
# from ...ModelServer.EmbeddingServer.utils import embedding_encode
# from ...ModelServer.ReRanker.utils import rerank_pairs
# import numpy as np


# class ES_DB_Control():
#     def __init__(self, es_url='http://192.168.8.125:9200', index_name='newtest01'):
#         # 创建Elasticsearch客户端对象
#         # self.es = Elasticsearch([es_url])
#         # 创建 Elasticsearch 客户端对象，显式设置头以避免兼容性问题
#         self.es = Elasticsearch([es_url], headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
#         # self.es = Elasticsearch(['http://127.0.0.1:11402'], timeout=30)
#         self.index_name = index_name

#     def create_index(self, vector_dims=1024):
#         mapping = {
#             "mappings": {
#                 "properties": {
#                     "db_name": {"type": "keyword"},
#                     "pagecontent": {"type": "text"},
#                     "offset_start": {"type": "integer"},
#                     "offset_end": {"type": "integer"},
#                     "embeddingvector": {"type": "dense_vector", "dims": vector_dims},
#                     "file_name": {"type": "keyword"}
#                 }
#             }
#         }
#         self.es.indices.create(index=self.index_name, body=mapping, ignore=400)

#     def UpChunks2DB(self, chunks):
#         documents = []
#         for chunk in chunks:
#             document = {
#                 "_index": self.index_name,
#                 "_type": "_doc",
#                 "_source": {
#                     "db_name": chunk.metadata.extracted_info["DBName"],
#                     "pagecontent": chunk.content,
#                     "offset_start": chunk.metadata.offset_start,
#                     "offset_end": chunk.metadata.offset_end,
#                     "embeddingvector": chunk.metadata.embeddingVector["embedding"],  # 嵌入向量字段
#                     "file_name": chunk.metadata.extracted_info["file_name"],
#                 }
#             }
#             documents.append(document)
#         # result = bulk(self.es, documents)
#         # 分片上传，一次性上传太多会有明显延迟
#         num = len(documents) // 100
#         for i in range(num + 1):
#             try:
#                 result = bulk(self.es, documents[100*i: 100*i+100])
#             except Exception as e:
#                 pass

#     def search_by_db_doc_name(self, db_name, doc_name):
#         try:
#             # 构建匹配查询
#             query = {
#                     "bool": {
#                         "must": [
#                             {"term": {"db_name.keyword": db_name}},
#                             {"term": {"file_name.keyword": doc_name}}
#                         ]
#                     }
#                 }
#             # 执行查询
#             result = self.es.search(index=self.index_name, body={"query": query}, size=10000)
#             # 获取匹配的文档ID列表
#             doc_ids = [doc["_id"] for doc in result["hits"]["hits"]]
#             # 执行多文档查询获取文档内容
#             docs = self.es.mget(index=self.index_name, body={"docs": [{"_id": doc_id} for doc_id in doc_ids]})
#             # 提取每个文档的内容
#             documents = [doc['_source'] for doc in docs['docs'] if doc['found']]
#             return documents
#         except Exception as e:
#             return []

#     def delete_document_by_db_and_doc_name(self, db_name, doc_names):
#         bulk_body = []
#         for doc_name in doc_names:
#             query = {
#                 "bool": {
#                     "must": [
#                         {"term": {"db_name.keyword": db_name}},
#                         {"term": {"file_name.keyword": doc_name}}
#                     ]
#                 }
#             }
#             # 使用查询语句检索要删除的文档ID
#             result = self.es.search(index=self.index_name, body={"query": query}, size=10000)
#             # 解析结果，提取文档ID
#             doc_ids = [doc["_id"] for doc in result["hits"]["hits"]]
#             for doc_id in doc_ids:
#                 bulk_body.append({"delete": {"_index": self.index_name, "_id": doc_id}})
#         # Perform bulk delete only if there are documents to delete
#         if bulk_body:
#             self.es.bulk(body=bulk_body)

#     def delete_documents_by_db_name(self, db_name):
#         # 构建查询语句
#         query = {
#             "query": {
#                 "term": {
#                     "db_name.keyword": db_name
#                 }
#             }
#         }
#         # 使用查询语句检索要删除的文档ID
#         result = self.es.search(index=self.index_name, body=query, size=10000)  # 一次最多获取1000个文档
#         # 解析结果，提取文档ID
#         doc_ids = [doc["_id"] for doc in result["hits"]["hits"]]
#         # 批量删除
#         bulk_body = [{"delete": {"_index": self.index_name, "_id": doc_id}} for doc_id in doc_ids]
#         self.es.bulk(body=bulk_body)
#         print(f"Deleted {len(doc_ids)} documents with db name '{db_name}'.")

#     # 查询所有DB_name
#     def get_unique_db_names_and_counts(self):
#         # 构建查询语句
#         query = {
#             "aggs": {
#                 "db_name_count": {
#                     "terms": {
#                         "field": "db_name.keyword",
#                         "size": 100
#                     }
#                 }
#             }
#         }
#         # 执行查询
#         try:
#             result = self.es.search(index=self.index_name, body=query)
#             # 解析结果
#             db_name_buckets = result["aggregations"]["db_name_count"]["buckets"]
#             db_name_info = []
#             for bucket in db_name_buckets:
#                 db_name = bucket["key"]
#                 count = bucket["doc_count"]
#                 db_name_info.append({"db_name": db_name, "count": count})

#         except exceptions.NotFoundError as e:
#             db_name_info = []
#         return db_name_info

#     # 查询不同标题的数量和标题列表
#     def get_unique_titles(self, db_name):
#         aggregation_query = {
#             "query": {
#                 "term": {
#                     "db_name.keyword": db_name
#                 }
#             },
#             "aggs": {
#                 "file_name_count": {
#                     "terms": {
#                         "field": "file_name.keyword",
#                         "size": 100  # 要返回的不同file_name数量
#                     }
#                 }
#             }
#         }
#         response = self.es.search(index=self.index_name, body=aggregation_query)
#         unique_titles_buckets = response["aggregations"]["file_name_count"]["buckets"]
#         unique_titles_count = len(unique_titles_buckets)
#         unique_titles = [bucket['key'] for bucket in unique_titles_buckets]
#         return unique_titles_count, unique_titles






# class ES_DB_search:
#     def __init__(self, 
#                  es_url='http://192.168.8.125:9200',
#                  index_name='newtest01'):
#         # 创建 Elasticsearch 客户端对象
#         self.es = Elasticsearch([es_url], headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
#         self.index_name = index_name

#     # 全文搜索查询
#     def full_text_search(self, db_name, query_text, n=5):
#         search_query = {
#             "query": {
#                 "bool": {
#                     "must": [
#                         {"term": {"db_name.keyword": db_name}},
#                         {"match": {"pagecontent": query_text}}
#                     ]
#                 }
#             },
#             "size": n
#         }
#         search_results = self.es.search(index=self.index_name, body=search_query)
#         documents = search_results['hits']['hits']
#         return documents

#     # BM25 搜索
#     def bm25_search(self, db_name, query_text, n=5):
#         search_query = {
#             "query": {
#                 "bool": {
#                     "must": [
#                         {"term": {"db_name.keyword": db_name}},
#                         {"match": {
#                             "pagecontent": {
#                                 "query": query_text,
#                                 "analyzer": "standard"
#                             }
#                         }}
#                     ]
#                 }
#             },
#             "size": 100,
#             "track_scores": True,
#             "min_score": 0
#         }
#         search_results = self.es.search(index=self.index_name, body=search_query)
#         documents = search_results['hits']['hits']
#         bm25_results = [(doc['_source']['pagecontent'],
#                         doc['_source']['db_name']) 
#                         for doc in documents]
#         return bm25_results[:n]

#     # Elasticsearch KNN 向量搜索
#     def vector_search_es(self, db_name, query_vector, n=5):
#         # 规范化 query_vector
#         query_vector = query_vector / np.linalg.norm(query_vector)

#         knn_query = {
#             "field": "embeddingvector",
#             "query_vector": query_vector,
#             "k": n,
#             "num_candidates": n * 5,
#             "filter": {
#                 "bool": {
#                     "must": [
#                         {"term": {"db_name.keyword": db_name}},
#                         {"exists": {"field": "embeddingvector"}}
#                     ]
#                 }
#             }
#         }
#         search_results = self.es.knn_search(index=self.index_name, knn=knn_query)
#         documents = search_results['hits']['hits']
#         return [(doc['_source']['pagecontent'], doc['_source']['db_name']) for doc in documents]

#     # 重排序
#     def reranker(self, query_text, nearest_pagecontents):
#         df = [[query_text, content[0]] for content in nearest_pagecontents]
#         reranker_scores_ = rerank_pairs(df)
#         reranker_scores = [score for score in reranker_scores_]

#         if isinstance(reranker_scores, float):
#             reranker_scores = [reranker_scores]

#         threshold = -10  # 设置阈值
#         combined_data = list(zip(reranker_scores, nearest_pagecontents))
#         combined_data.sort(reverse=True, key=lambda x: x[0])

#         if combined_data[0][0] < threshold:
#             reranker_nearest_pagecontents = []
#             reranker_scores_sorted = []
#         else:
#             reranker_nearest_pagecontents = [x[1] for x in combined_data]
#             reranker_scores_sorted = [(x[0] + 10) / 20 for x in combined_data]
#         return reranker_nearest_pagecontents, reranker_scores_sorted

#     # 单数据库混合搜索
#     def hybrid_search(self, db_name, query_text, n):
#         query_vector = embedding_encode(query_text)
#         print("Query Vector:", query_vector)
#         print("Vector Type:", type(query_vector))
#         print("Element Types:", [type(x) for x in query_vector])
        
#         bm25_results = self.bm25_search(db_name, query_text, n)
#         vector_results = self.vector_search_es(db_name, query_vector, n)
#         combined_results = list(set(bm25_results + vector_results))
#         reranker_nearest_pagecontents, reranker_scores_sorted = self.reranker(query_text, combined_results)
#         return reranker_nearest_pagecontents[:n], reranker_scores_sorted[:n]

#     # 多数据库混合搜索
#     def hybrid_search_multydb(self, db_names, query_text, n):
#         query_vector = embedding_encode(query_text)
#         combined_results = []
#         for db_name in db_names:
#             bm25_results = self.bm25_search(db_name, query_text, n)
#             vector_results = self.vector_search_es(db_name, query_vector, n)
#             db_results = list(set(bm25_results + vector_results))
#             combined_results.extend(db_results)

#         reranker_nearest_pagecontents, reranker_scores_sorted = self.reranker(query_text, combined_results)
#         if len(reranker_nearest_pagecontents) <= n:
#             return (reranker_nearest_pagecontents[:len(reranker_nearest_pagecontents)], 
#                     reranker_scores_sorted[:len(reranker_scores_sorted)])
#         return reranker_nearest_pagecontents[:n], reranker_scores_sorted[:n]







# from elasticsearch import Elasticsearch
# from elasticsearch import exceptions
# from elasticsearch.helpers import bulk
# from sklearn.neighbors import KDTree
# import os
# import numpy as np
# from ...ModelServer.EmbeddingServer.utils import embedding_encode
# from ...ModelServer.ReRanker.utils import rerank_pairs


# class ES_DB_Control:
#     def __init__(self, 
#                  es_url='http://192.168.8.125:9200',
#                  index_name='newtest01'):
#         # 创建 Elasticsearch 客户端对象，显式设置头以避免兼容性问题
#         self.es = Elasticsearch([es_url], 
#                                headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
#         self.index_name = index_name

#     def create_index(self, vector_dims=1024):
#         mapping = {
#             "mappings": {
#                 "properties": {
#                     "db_name": {"type": "keyword"},
#                     "pagecontent": {"type": "text"},
#                     "offset_start": {"type": "integer"},
#                     "offset_end": {"type": "integer"},
#                     "embeddingvector": {"type": "dense_vector", "dims": vector_dims},
#                     "file_name": {"type": "keyword"}
#                 }
#             }
#         }
#         try:
#             self.es.indices.create(index=self.index_name, body=mapping, ignore=400)
#             print(f"Index '{self.index_name}' created or already exists.")
#         except Exception as e:
#             print(f"Error creating index: {e}")

#     def UpChunks2DB(self, chunks):
#         documents = []
#         for chunk in chunks:
#             document = {
#                 "_index": self.index_name,
#                 "_type": "_doc",
#                 "_source": {
#                     "db_name": chunk.metadata.extracted_info["DBName"],
#                     "pagecontent": chunk.content,
#                     "offset_start": chunk.metadata.offset_start,
#                     "offset_end": chunk.metadata.offset_end,
#                     "embeddingvector": chunk.metadata.embeddingVector["embedding"],
#                     "file_name": chunk.metadata.extracted_info["file_name"],
#                 }
#             }
#             documents.append(document)
#         num = len(documents) // 100
#         for i in range(num + 1):
#             try:
#                 bulk(self.es, documents[100*i: 100*i+100])
#             except Exception as e:
#                 print(f"Error uploading chunk {i}: {e}")

#     def search_by_db_doc_name(self, db_name, doc_name):
#         try:
#             query = {
#                 "bool": {
#                     "must": [
#                         {"term": {"db_name.keyword": db_name}},
#                         {"term": {"file_name.keyword": doc_name}}
#                     ]
#                 }
#             }
#             result = self.es.search(index=self.index_name, body={"query": query}, size=10000)
#             doc_ids = [doc["_id"] for doc in result["hits"]["hits"]]
#             docs = self.es.mget(index=self.index_name, body={"docs": [{"_id": doc_id} for doc_id in doc_ids]})
#             documents = [doc['_source'] for doc in docs['docs'] if doc['found']]
#             return documents
#         except Exception as e:
#             print(f"Search error: {e}")
#             return []

#     def delete_document_by_db_and_doc_name(self, db_name, doc_names):
#         bulk_body = []
#         for doc_name in doc_names:
#             query = {
#                 "bool": {
#                     "must": [
#                         {"term": {"db_name.keyword": db_name}},
#                         {"term": {"file_name.keyword": doc_name}}
#                     ]
#                 }
#             }
#             result = self.es.search(index=self.index_name, body={"query": query}, size=10000)
#             doc_ids = [doc["_id"] for doc in result["hits"]["hits"]]
#             for doc_id in doc_ids:
#                 bulk_body.append({"delete": {"_index": self.index_name, "_id": doc_id}})
#         if bulk_body:
#             try:
#                 self.es.bulk(body=bulk_body)
#                 print(f"Deleted {len(bulk_body)} documents.")
#             except Exception as e:
#                 print(f"Error deleting documents: {e}")

#     def delete_documents_by_db_name(self, db_name):
#         query = {
#             "query": {
#                 "term": {
#                     "db_name.keyword": db_name
#                 }
#             }
#         }
#         try:
#             result = self.es.search(index=self.index_name, body=query, size=10000)
#             doc_ids = [doc["_id"] for doc in result["hits"]["hits"]]
#             bulk_body = [{"delete": {"_index": self.index_name, "_id": doc_id}} for doc_id in doc_ids]
#             self.es.bulk(body=bulk_body)
#             print(f"Deleted {len(doc_ids)} documents with db name '{db_name}'.")
#         except Exception as e:
#             print(f"Error deleting by db_name: {e}")

#     def get_unique_db_names_and_counts(self):
#         query = {
#             "aggs": {
#                 "db_name_count": {
#                     "terms": {
#                         "field": "db_name.keyword",
#                         "size": 100
#                     }
#                 }
#             }
#         }
#         try:
#             result = self.es.search(index=self.index_name, body=query)
#             db_name_buckets = result["aggregations"]["db_name_count"]["buckets"]
#             db_name_info = [{"db_name": bucket["key"], "count": bucket["doc_count"]} for bucket in db_name_buckets]
#             return db_name_info
#         except exceptions.NotFoundError as e:
#             print(f"Index not found: {e}")
#             return []
#         except Exception as e:
#             print(f"Error in get_unique_db_names_and_counts: {e}")
#             return []

#     def get_unique_titles(self, db_name):
#         aggregation_query = {
#             "query": {
#                 "term": {
#                     "db_name.keyword": db_name
#                 }
#             },
#             "aggs": {
#                 "file_name_count": {
#                     "terms": {
#                         "field": "file_name.keyword",
#                         "size": 100
#                     }
#                 }
#             }
#         }
#         try:
#             response = self.es.search(index=self.index_name, body=aggregation_query)
#             unique_titles_buckets = response["aggregations"]["file_name_count"]["buckets"]
#             unique_titles_count = len(unique_titles_buckets)
#             unique_titles = [bucket['key'] for bucket in unique_titles_buckets]
#             return unique_titles_count, unique_titles
#         except Exception as e:
#             print(f"Error in get_unique_titles: {e}")
#             return 0, []


# class ES_DB_search:
#     def __init__(self, 
#                  es_url='http://192.168.8.125:9200',
#                  index_name='newtest01'):
#         self.es = Elasticsearch([es_url], 
#                                headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
#         self.index_name = index_name

#     def full_text_search(self, db_name, query_text, n=5):
#         search_query = {
#             "query": {
#                 "bool": {
#                     "must": [
#                         {"term": {"db_name.keyword": db_name}},
#                         {"match": {"pagecontent": query_text}}
#                     ]
#                 }
#             },
#             "size": n
#         }
#         try:
#             search_results = self.es.search(index=self.index_name, body=search_query)
#             documents = search_results['hits']['hits']
#             return documents
#         except Exception as e:
#             print(f"Error in full_text_search: {e}")
#             return []

#     def bm25_search(self, db_name, query_text, n=5):
#         search_query = {
#             "query": {
#                 "bool": {
#                     "must": [
#                         {"term": {"db_name.keyword": db_name}},
#                         {"match": {
#                             "pagecontent": {
#                                 "query": query_text,
#                                 "analyzer": "standard"
#                             }
#                         }}
#                     ]
#                 }
#             },
#             "size": 100,
#             "track_scores": True,
#             "min_score": 0
#         }
#         try:
#             search_results = self.es.search(index=self.index_name, body=search_query)
#             documents = search_results['hits']['hits']
#             bm25_results = [(doc['_source']['pagecontent'], doc['_source']['db_name']) for doc in documents]
#             return bm25_results[:n]
#         except Exception as e:
#             print(f"Error in bm25_search: {e}")
#             return []

#     def vector_search_es(self, db_name, query_vector, n=5):
#         query_vector = query_vector / np.linalg.norm(query_vector)
#         knn_query = {
#             "field": "embeddingvector",
#             "query_vector": query_vector,
#             "k": n,
#             "num_candidates": n * 5,
#             "filter": {
#                 "bool": {
#                     "must": [
#                         {"term": {"db_name.keyword": db_name}},
#                         {"exists": {"field": "embeddingvector"}}
#                     ]
#                 }
#             }
#         }
#         try:
#             search_results = self.es.knn_search(index=self.index_name, knn=knn_query)
#             documents = search_results['hits']['hits']
#             return [(doc['_source']['pagecontent'], doc['_source']['db_name']) for doc in documents]
#         except Exception as e:
#             print(f"Error in vector_search_es: {e}")
#             return []

#     def reranker(self, query_text, nearest_pagecontents):
#         df = [[query_text, content[0]] for content in nearest_pagecontents]
#         reranker_scores_ = rerank_pairs(df)
#         reranker_scores = [score for score in reranker_scores_]

#         if isinstance(reranker_scores, float):
#             reranker_scores = [reranker_scores]

#         threshold = -10
#         combined_data = list(zip(reranker_scores, nearest_pagecontents))
#         combined_data.sort(reverse=True, key=lambda x: x[0])

#         if combined_data[0][0] < threshold:
#             reranker_nearest_pagecontents = []
#             reranker_scores_sorted = []
#         else:
#             reranker_nearest_pagecontents = [x[1] for x in combined_data]
#             reranker_scores_sorted = [(x[0] + 10) / 20 for x in combined_data]
#         return reranker_nearest_pagecontents, reranker_scores_sorted

#     def hybrid_search(self, db_name, query_text, n):
#         query_vector = embedding_encode(query_text)
#         try:
#             bm25_results = self.bm25_search(db_name, query_text, n)
#             vector_results = self.vector_search_es(db_name, query_vector, n)
#             combined_results = list(set(bm25_results + vector_results))
#             reranker_nearest_pagecontents, reranker_scores_sorted = self.reranker(query_text, combined_results)
#             return reranker_nearest_pagecontents[:n], reranker_scores_sorted[:n]
#         except Exception as e:
#             print(f"Error in hybrid_search: {e}")
#             return [], []

#     def hybrid_search_multydb(self, db_names, query_text, n):
#         query_vector = embedding_encode(query_text)
#         combined_results = []
#         for db_name in db_names:
#             try:
#                 bm25_results = self.bm25_search(db_name, query_text, n)
#                 vector_results = self.vector_search_es(db_name, query_vector, n)
#                 db_results = list(set(bm25_results + vector_results))
#                 combined_results.extend(db_results)
#             except Exception as e:
#                 print(f"Error in hybrid_search_multydb for {db_name}: {e}")
#         try:
#             reranker_nearest_pagecontents, reranker_scores_sorted = self.reranker(query_text, combined_results)
#             if len(reranker_nearest_pagecontents) <= n:
#                 return (reranker_nearest_pagecontents, reranker_scores_sorted)
#             return reranker_nearest_pagecontents[:n], reranker_scores_sorted[:n]
#         except Exception as e:
#             print(f"Error in reranker for multi-db: {e}")
#             return [], []