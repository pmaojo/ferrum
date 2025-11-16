class SlowAPIMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # For the stub implementation, just pass through to the wrapped app
        await self.app(scope, receive, send)
