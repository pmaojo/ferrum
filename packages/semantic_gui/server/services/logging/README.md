# Logging Infrastructure

This logging infrastructure replaces console statements with structured logging using Winston.

## Features

- **Environment-based configuration**: Different log levels for development vs production
- **Component-specific loggers**: Each component gets its own logger with contextual information
- **Structured logging**: JSON format in production, human-readable in development
- **Error handling**: Fallback to console if Winston fails
- **TypeScript support**: Full type safety with interfaces

## Usage

### Basic Usage

```typescript
import { createLogger } from './services/logging';

const logger = createLogger('my-component');

logger.debug('Debug message', { userId: 123 });
logger.info('Info message', { action: 'user-login' });
logger.warn('Warning message', { issue: 'deprecated-api' });
logger.error('Error message', new Error('Something went wrong'), { context: 'additional-info' });
```

### Using Logger Factory

```typescript
import { LoggerFactory } from './services/logging';

// Create specific types of loggers
const routeLogger = LoggerFactory.createRouteLogger('api');
const serviceLogger = LoggerFactory.createServiceLogger('database');
const middlewareLogger = LoggerFactory.createMiddlewareLogger('auth');
const utilityLogger = LoggerFactory.createUtilityLogger('parser');
```

### Using Convenience Loggers

```typescript
import { expressLogger, databaseLogger, websocketLogger } from './services/logging';

const port = Number(process.env.PORT) || 3000;
expressLogger.info('Server started', { port });
databaseLogger.error('Connection failed', error, { host: 'localhost' });
websocketLogger.debug('Client connected', { clientId: 'abc123' });
```

## Configuration

The logger automatically configures based on environment variables:

- `NODE_ENV`: Controls output format (development = human-readable, production = JSON)
- `LOG_LEVEL`: Controls minimum log level (debug, info, warn, error)

## Migration from Console Statements

### Before
```typescript
console.log('User logged in:', userId);
console.error('Database error:', error);
console.warn('Deprecated API used');
```

### After
```typescript
import { createLogger } from './services/logging';
const logger = createLogger('auth');

logger.info('User logged in', { userId });
logger.error('Database error', error);
logger.warn('Deprecated API used');
```

## Log Levels

- **debug**: Detailed information for debugging
- **info**: General information about application flow
- **warn**: Warning messages for potential issues
- **error**: Error messages with optional Error objects

## Output Examples

### Development
```
2025-08-10T11:06:02.866Z info [auth] User logged in {"userId": 123}
2025-08-10T11:06:02.867Z error [database] Connection failed {"host": "localhost", "error": {"name": "Error", "message": "Connection timeout"}}
```

### Production
```json
{"timestamp":"2025-08-10T11:06:02.866Z","level":"info","message":"User logged in","component":"auth","userId":123}
{"timestamp":"2025-08-10T11:06:02.867Z","level":"error","message":"Connection failed","component":"database","host":"localhost","error":{"name":"Error","message":"Connection timeout","stack":"..."}}
```