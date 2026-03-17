module.exports = {
  apps: [
    {
      name: "llmeval-backend",
      cwd: "./backend",
      script: ".venv/bin/uvicorn",
      args: "main:app --host 0.0.0.0 --port 8000 --reload",
      interpreter: "none",
      env: {
        DATABASE_URL: "postgresql+asyncpg://llmeval:llmeval123@localhost:5432/llmeval",
        REDIS_URL: "redis://localhost:6379/0",
        // Uncomment below if you need HTTP proxy for external API calls
        // HTTP_PROXY: "http://127.0.0.1:7890",
        // HTTPS_PROXY: "http://127.0.0.1:7890",
        // NO_PROXY: "localhost,127.0.0.1,::1",
      },
      watch: false,
      max_restarts: 10,
      restart_delay: 3000,
    },
    {
      name: "llmeval-celery",
      cwd: "./backend",
      script: ".venv/bin/celery",
      args: "-A app.core.celery_app worker --loglevel=info --concurrency=2 -Q celery,evaluation",
      interpreter: "none",
      env: {
        DATABASE_URL: "postgresql+asyncpg://llmeval:llmeval123@localhost:5432/llmeval",
        REDIS_URL: "redis://localhost:6379/0",
        // Uncomment below if you need HTTP proxy for external API calls
        // HTTP_PROXY: "http://127.0.0.1:7890",
        // HTTPS_PROXY: "http://127.0.0.1:7890",
        // NO_PROXY: "localhost,127.0.0.1,::1",
      },
      watch: false,
      max_restarts: 10,
      restart_delay: 5000,
    },
    {
      name: "llmeval-frontend",
      cwd: "./frontend",
      script: "node_modules/.bin/next",
      args: "start -H 0.0.0.0 -p 3000",
      interpreter: "none",
      watch: false,
      max_restarts: 10,
      restart_delay: 3000,
    },
  ],
};
