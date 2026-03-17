const dotenv = require("dotenv");
const path = require("path");

const env = dotenv.config({ path: path.resolve(__dirname, ".env") }).parsed || {};

const isWindows = process.platform === "win32";
const venvBin = isWindows ? ".venv\\Scripts" : ".venv/bin";

const DB_USER = env.DB_USER || "llmeval";
const DB_PASS = env.DB_PASS || "llmeval123";
const DB_HOST = env.DB_HOST || "localhost";
const DB_PORT = env.DB_PORT || "5432";
const DB_NAME = env.DB_NAME || "llmeval";
const REDIS_HOST = env.REDIS_HOST || "localhost";
const REDIS_PORT = env.REDIS_PORT || "6379";
const BACKEND_PORT = env.BACKEND_PORT || "8000";
const FRONTEND_PORT = env.FRONTEND_PORT || "3000";
const HOST_IP = env.HOST_IP || "localhost";

const DATABASE_URL = `postgresql+asyncpg://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}`;
const DATABASE_URL_SYNC = `postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}`;
const REDIS_URL = `redis://${REDIS_HOST}:${REDIS_PORT}/0`;
const CELERY_BROKER_URL = `redis://${REDIS_HOST}:${REDIS_PORT}/1`;
const CELERY_RESULT_BACKEND = `redis://${REDIS_HOST}:${REDIS_PORT}/2`;

const HTTP_PROXY = env.HTTP_PROXY || "";
const HTTPS_PROXY = env.HTTPS_PROXY || "";
const NO_PROXY = env.NO_PROXY || "localhost,127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16";

const commonEnv = {
  DATABASE_URL,
  DATABASE_URL_SYNC,
  REDIS_URL,
  CELERY_BROKER_URL,
  CELERY_RESULT_BACKEND,
  MINIO_ENDPOINT: env.MINIO_ENDPOINT || "localhost:9000",
  MINIO_ACCESS_KEY: env.MINIO_ACCESS_KEY || "minioadmin",
  MINIO_SECRET_KEY: env.MINIO_SECRET_KEY || "minioadmin123",
  SECRET_KEY: env.SECRET_KEY || "supersecretkey-change-in-production",
  HOST_IP,
  FRONTEND_PORT,
  CORS_EXTRA_ORIGINS: env.CORS_EXTRA_ORIGINS || "",
  HTTP_PROXY,
  http_proxy: HTTP_PROXY,
  HTTPS_PROXY,
  https_proxy: HTTPS_PROXY,
  NO_PROXY,
  no_proxy: NO_PROXY,
  ALL_PROXY: "",
  all_proxy: "",
};

module.exports = {
  apps: [
    {
      name: "llmeval-backend",
      cwd: "./backend",
      script: `${venvBin}${isWindows ? "\\" : "/"}uvicorn`,
      args: `main:app --host 0.0.0.0 --port ${BACKEND_PORT} --reload`,
      interpreter: "none",
      env: commonEnv,
      watch: false,
      max_restarts: 10,
      restart_delay: 3000,
    },
    {
      name: "llmeval-celery",
      cwd: "./backend",
      script: `${venvBin}${isWindows ? "\\" : "/"}celery`,
      args: `-A app.core.celery_app worker --loglevel=info --concurrency=2 -Q celery,evaluation${isWindows ? " --pool=solo" : ""}`,
      interpreter: "none",
      env: commonEnv,
      watch: false,
      max_restarts: 10,
      restart_delay: 5000,
    },
    {
      name: "llmeval-frontend",
      cwd: "./frontend",
      script: "node_modules/.bin/next",
      args: `start -H 0.0.0.0 -p ${FRONTEND_PORT}`,
      interpreter: "none",
      env: {
        NEXT_PUBLIC_API_URL: `http://${HOST_IP}:${BACKEND_PORT}`,
      },
      watch: false,
      max_restarts: 10,
      restart_delay: 3000,
    },
  ],
};
