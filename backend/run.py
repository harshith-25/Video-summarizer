import uvicorn
from app.main import create_app

app = create_app()

if __name__ == '__main__':
    # Replicates Flask run command using Uvicorn
    # host 0.0.0.0 enables desktop integrations
    uvicorn.run(
        "run:app", 
        host="0.0.0.0", 
        port=7898, 
        reload=True
    )