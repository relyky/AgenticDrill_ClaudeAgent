import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

load_dotenv() # 這會讀取 .env 檔案

# 定義 model
class QueryRequest(BaseModel):
    query: str

# 設定 logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,      # Config.LOG_LEVEL,
    filename=None,            # Config.LOG_FILENAME,
    encoding="utf-8",
)

logger = logging.getLogger(__name__)

# 設定 FastAPI
app = FastAPI()

# CORS
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

@app.post("/query")
async def handle_query(request: QueryRequest):
    try:
        logger.debug("entry handle_query")
        now = datetime.now()
        
        return {
            "received_time": now,
			"responseText": "你好。我來自 Claude Agent Drill",
		}

    except Exception as e:
        return {"error":str(e)}

#def main():
#    logger.info("系統啟始")
#
#if __name__ == "__main__":
#    main()