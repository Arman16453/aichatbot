from backend.main import app

"""Top-level app entrypoint so `py -m uvicorn main:app` works when run from the isro-helpbot folder."""

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
