import { createProxyMiddleware } from 'http-proxy-middleware';

export default function handler(req, res) {
  const { path } = req.query;
  const target = process.env.BACKEND_URL || 'http://127.0.0.1:5001';
  
  // Create proxy
  const proxy = createProxyMiddleware({
    target: `${target}/api/${path.join('/')}`,
    changeOrigin: true,
    pathRewrite: {
      '^/api': '', // Remove /api prefix when forwarding
    },
  });

  return new Promise((resolve, reject) => {
    proxy(req, res, (result) => {
      if (result instanceof Error) {
        return reject(result);
      }
      return resolve(result);
    });
  });
}

export const config = {
  api: {
    bodyParser: false,
  },
}; 