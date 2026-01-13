from .ryuo import Ryuo
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
import shutil
import os
from typing import Any
import tempfile


def make_app(ryuo: Ryuo) -> FastAPI:
    app = FastAPI(title="Ryuo API")

    @app.get("/list")
    def list_media():
        try:
            media = ryuo.get_media_files()
            return JSONResponse(content={"media": media})
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/info")
    def info():
        try:
            cfg = ryuo.config.settings
            return JSONResponse(content={"config": cfg})
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/upload")
    async def upload(file: UploadFile = File(...)):
        if not file.filename.lower().endswith(".mp4"):
            raise HTTPException(status_code=400, detail="Only .mp4 files are supported")
        # save to a temporary path then invoke upload
        try:
            tmp_dir = os.path.join(os.getcwd(), "tmp_uploads")
            os.makedirs(tmp_dir, exist_ok=True)
            dest = os.path.join(tmp_dir, os.path.basename(file.filename))
            with open(dest, "wb") as out_f:
                shutil.copyfileobj(file.file, out_f)
            try:
                ryuo.upload(dest)
                return JSONResponse(content={"uploaded": file.filename})
            finally:
                try:
                    if os.path.exists(dest):
                        os.remove(dest)
                except Exception:
                    pass
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/delete/{media}")
    def delete_media(media: str):
        try:
            media_files = ryuo.get_media_files()
            if media not in media_files:
                raise HTTPException(status_code=404, detail="Media not found")
            ryuo.delete(media)
            # if it was active, clear
            try:
                if ryuo.config.settings.get("media") == media:
                    ryuo.set_media("")
            except Exception:
                pass
            return JSONResponse(content={"deleted": media})
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/set/{media}/{brightness}")
    def set_media_brightness(media: str, brightness: int):
        try:
            try:
                brightness = int(brightness)
            except Exception:
                raise HTTPException(status_code=400, detail="Brightness must be an integer")
            if brightness < 0 or brightness > 255:
                raise HTTPException(status_code=400, detail="Brightness must be between 0 and 255")

            media_files = ryuo.get_media_files()
            if media not in media_files:
                raise HTTPException(status_code=404, detail="Media not found on device")

            ryuo.set_media(media)
            ryuo.set_brightness(brightness)
            try:
                ryuo.config.save_config()
            except Exception:
                pass
            return JSONResponse(content={"media": media, "brightness": brightness})
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/brightness/{brightness}")
    def set_brightness_only(brightness: int):
        try:
            try:
                brightness = int(brightness)
            except Exception:
                raise HTTPException(status_code=400, detail="Brightness must be an integer")
            if brightness < 0 or brightness > 255:
                raise HTTPException(status_code=400, detail="Brightness must be between 0 and 255")

            # apply brightness to current media only
            ryuo.set_brightness(brightness)
            try:
                ryuo.config.save_config()
            except Exception:
                pass
            return JSONResponse(content={"brightness": brightness})
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/download/{media}")
    def download_media(media: str, background_tasks: BackgroundTasks):
        try:
            media_files = ryuo.get_media_files()
            if media not in media_files:
                raise HTTPException(status_code=404, detail="Media not found")

            tmp_dir = os.path.join(os.getcwd(), "tmp_downloads")
            os.makedirs(tmp_dir, exist_ok=True)
            dest = os.path.join(tmp_dir, os.path.basename(media))

            # perform device download to temporary file
            ryuo.download(media, dest)

            def _safe_remove(path: str) -> None:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass

            background_tasks.add_task(_safe_remove, dest)

            return FileResponse(dest, media_type="video/mp4", filename=os.path.basename(media))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


class API:
    def __init__(self, host: str = "127.0.0.1", port: int = 55667):
        self.ryuo = Ryuo()
        self.host = host
        self.port = port
        self.app = make_app(self.ryuo)

    def run(self):
        # run uvicorn programmatically
        uvicorn.run(self.app, host=self.host, port=self.port)