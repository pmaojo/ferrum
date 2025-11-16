import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';
import { ConfigProvider } from './context/ConfigContext';

async function bootstrap() {
  try {
    const res = await fetch('/config');
    if (!res.ok) {
      throw new Error(`Config fetch failed: ${res.status}`);
    }
    const config = await res.json();
    createRoot(document.getElementById('root')!).render(
      <ConfigProvider config={config}>
        <App />
      </ConfigProvider>
    );
  } catch (error) {
    console.error('Failed to load config, using defaults:', error);
    // Fallback to default config
    const defaultConfig = { flags: {} };
    createRoot(document.getElementById('root')!).render(
      <ConfigProvider config={defaultConfig}>
        <App />
      </ConfigProvider>
    );
  }
}

bootstrap();
