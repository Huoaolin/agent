import os
import sys
import asyncio
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append(os.path.abspath("./src"))

from src.agent import Agent


app = FastAPI(title="BrowseControl API")


class UserInput(BaseModel):
    input: str
    jobID: str = None  # 添加 jobID 参数，默认为 None，可选


@app.post("/process", response_model=dict)
async def process_user_input(user_input: UserInput):
    logger.info(f"Received input: {user_input.input}, jobID: {user_input.jobID}")
    try:
        agent = Agent(jobID=user_input.jobID)  # 在初始化时传入 jobID
        logger.info(f"Agent initialized with jobID: {user_input.jobID}")
        results = await agent.run(user_input.input)
        logger.info(f"Results: {results}")
        return {"status": "success", "input": user_input.input, "jobID": user_input.jobID, "results": results}
    except Exception as e:
        logger.error(f"Error processing input '{user_input.input}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")