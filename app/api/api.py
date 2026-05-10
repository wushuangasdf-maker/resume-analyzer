from fastapi import FastAPI,UploadFile,File
from app.parsers.parser import parse_resume
from app.utils.utils import limit_text

import logging
import shutil
import os

app = FastAPI()
UPLOAD_DIR = "../../uploads"
os.makedirs(UPLOAD_DIR,exist_ok=True)
logging.basicConfig(level=logging.INFO)

@app.post("/analyze")
async  def analyze(file:UploadFile=File(...)):
    try:
        logging.info("收到文件开始上次")
        #保存文件
        file_path=os.path.join(UPLOAD_DIR,file.filename)
        with open(file_path,"wb") as buffer:
            shutil.copyfileobj(file.file,buffer)
        logging.info(f"文件已经上传:{file.filename}")
        logging.info(f"文件开始解析")
        #解析简历
        text=parse_resume(file_path)
        if not text:
            return {
                "code":400,
                "message":"简历内容为空",
                "data":None
                }
        logging.info(f"解析完毕，文本长度为：{len(text)}")
        #截断简历
        text=limit_text(text)
        logging.info("经行简历文本截断处理")

        #ai分析
        logging.info("经行AI分析")
        result=analyze_resume_v2(text)
        logging.info("AI分析完毕")
        return {
            "code":200,
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
            "code": 200,
            "message": "error",
            "data":str(e)
        }