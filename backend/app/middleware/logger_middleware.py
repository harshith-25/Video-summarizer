from fastapi import Request
import time
import logging

logger = logging.getLogger("app")

async def logger_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    # Extract client IP
    client_ip = "unknown"
    if request.client:
        client_ip = request.client.host
        
    logger.info(
        f'{request.method} {request.url.path} - '
        f'Status: {response.status_code} - '
        f'Duration: {duration:.3f}s - '
        f'IP: {client_ip}'
    )
    
    return response