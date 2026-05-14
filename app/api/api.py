from fastapi import FastAPI, UploadFile, File, APIRouter
from app.parsers import file_router
from app.services import resume_analyzer
import logging
import shutil
import os

router=APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR,exist_ok=True)
#日志配置
logging.basicConfig(level=logging.INFO)

@router.get("/ping")
def ping():
    return {"message":"ping"}

@router.post("/analyze")
async def analyze(file:UploadFile=File(...)):
    try:
        logging.info("收到文件开始上次")
        #保存文件
        file_path=os.path.join(UPLOAD_DIR,file.filename)
        with open(file_path,"wb") as buffer:
            shutil.copyfileobj(file.file,buffer)
        logging.info(f"文件已经上传:{file.filename}")
        logging.info(f"文件开始解析")
        #解析简历
        text=file_router.parse_resume(file_path)
        if not text:
            return {
                "code":400,
                "message":"简历内容为空",
                "data":None
                }
        logging.info(f"解析完毕，文本长度为：{len(text)}")


        #ai分析
        logging.info("经行AI分析")
        result=resume_analyzer.analyze_resume_v2(text)
        logging.info("AI分析完毕")
        return {
            "code":500,
            "message":"success",
            "data":
            {
            "filename":file.filename,
            "analysis":result
            }
        }
    except Exception as e:
        logging.error(f"发生错误：{str(e)}")
        return {
            "code": 500,
            "message": "error",
            "data":str(e)
        }