#!/usr/bin/env python3
"""
Скрипт для генерации нагрузки на API для тестирования метрик.
"""
import asyncio
import aiohttp
import time
import random
from typing import List
import argparse


class LoadGenerator:
    def __init__(self, base_url: str, concurrent_requests: int = 10):
        self.base_url = base_url.rstrip('/')
        self.concurrent_requests = concurrent_requests
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> bool:
        """Проверка доступности API."""
        try:
            async with self.session.get(f"{self.base_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status == 200
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
    
    async def make_request(self, endpoint: str, method: str = "GET", **kwargs):
        """Выполнение HTTP запроса."""
        url = f"{self.base_url}{endpoint}"
        try:
            async with self.session.request(method, url, timeout=aiohttp.ClientTimeout(total=30), **kwargs) as response:
                await response.read()  # Читаем ответ полностью
                return {
                    "status": response.status,
                    "endpoint": endpoint,
                    "method": method
                }
        except Exception as e:
            return {
                "status": 0,
                "endpoint": endpoint,
                "method": method,
                "error": str(e)
            }
    
    async def generate_load(self, duration: int = 60, requests_per_second: int = 10):
        """Генерация нагрузки."""
        print(f"Starting load generation:")
        print(f"  Base URL: {self.base_url}")
        print(f"  Duration: {duration} seconds")
        print(f"  Requests per second: {requests_per_second}")
        print(f"  Concurrent requests: {self.concurrent_requests}")
        print()
        
        # Проверка доступности
        if not await self.health_check():
            print("ERROR: API is not available!")
            return
        
        print("API is available. Starting load generation...")
        print()
        
        # Эндпоинты для тестирования
        endpoints = [
            ("/health", "GET"),
            ("/", "GET"),
            ("/api/docs", "GET"),
            ("/api/v1/auth/me", "GET"),  # Вернет 401, но создаст метрики
            ("/metrics", "GET"),
        ]
        
        start_time = time.time()
        request_count = 0
        error_count = 0
        
        async def worker():
            nonlocal request_count, error_count
            while time.time() - start_time < duration:
                endpoint, method = random.choice(endpoints)
                result = await self.make_request(endpoint, method)
                request_count += 1
                
                if result["status"] == 0 or result["status"] >= 400:
                    error_count += 1
                
                # Контроль скорости запросов
                await asyncio.sleep(1.0 / requests_per_second)
        
        # Запуск воркеров
        workers = [worker() for _ in range(self.concurrent_requests)]
        await asyncio.gather(*workers)
        
        elapsed = time.time() - start_time
        print()
        print("=" * 50)
        print("Load generation completed!")
        print(f"  Duration: {elapsed:.2f} seconds")
        print(f"  Total requests: {request_count}")
        print(f"  Errors: {error_count}")
        print(f"  Success rate: {(request_count - error_count) / request_count * 100:.2f}%")
        print(f"  Requests/sec: {request_count / elapsed:.2f}")
        print("=" * 50)


async def main():
    parser = argparse.ArgumentParser(description="Load generator for MediAudit API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument("--rps", type=int, default=10, help="Requests per second")
    parser.add_argument("--concurrent", type=int, default=10, help="Concurrent requests")
    
    args = parser.parse_args()
    
    async with LoadGenerator(args.url, args.concurrent) as generator:
        await generator.generate_load(args.duration, args.rps)


if __name__ == "__main__":
    asyncio.run(main())





