# Deployment Guide for GitHired

This guide will help you deploy your GitHired application on Vercel.

## Prerequisites

1. **GitHub Account**: Your code should be in a GitHub repository
2. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
3. **Backend Platform Account**: Railway, Render, or Heroku for the Flask backend

## Step 1: Deploy Backend

### Option A: Deploy on Railway (Recommended)

1. Go to [railway.app](https://railway.app) and sign up
2. Create a new project
3. Connect your GitHub repository
4. Select the `backend` folder as the source
5. Add environment variables:
   ```
   MONGODB_URI=your_mongodb_connection_string
   GITHUB_TOKEN=your_github_token
   GEMINI_API_KEY=your_gemini_api_key
   ```
6. Deploy the project
7. Copy the generated URL (e.g., `https://your-app.railway.app`)

### Option B: Deploy on Render

1. Go to [render.com](https://render.com) and sign up
2. Create a new Web Service
3. Connect your GitHub repository
4. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Root Directory**: `backend`
5. Add environment variables (same as above)
6. Deploy and copy the URL

### Option C: Deploy on Heroku

1. Install Heroku CLI
2. Run these commands:
   ```bash
   cd backend
   heroku create your-app-name
   heroku config:set MONGODB_URI=your_mongodb_connection_string
   heroku config:set GITHUB_TOKEN=your_github_token
   heroku config:set GEMINI_API_KEY=your_gemini_api_key
   git push heroku main
   ```

## Step 2: Deploy Frontend on Vercel

1. **Connect Repository**:
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import your GitHub repository
   - Set the root directory to `frontend`

2. **Configure Build Settings**:
   - Framework Preset: Next.js
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `.next`
   - Install Command: `npm install`

3. **Add Environment Variables**:
   - Go to Project Settings → Environment Variables
   - Add: `NEXT_PUBLIC_API_URL` = `your_backend_url` (from Step 1)

4. **Deploy**:
   - Click "Deploy"
   - Vercel will automatically build and deploy your app

## Step 3: Configure Custom Domain (Optional)

1. In your Vercel project settings, go to "Domains"
2. Add your custom domain
3. Configure DNS settings as instructed

## Environment Variables

Make sure to set these environment variables in your backend deployment:

### Required:
- `MONGODB_URI`: Your MongoDB connection string
- `GITHUB_TOKEN`: GitHub personal access token
- `GEMINI_API_KEY`: Google Gemini API key

### Optional:
- `FLASK_ENV`: Set to `production` for production deployment

## Troubleshooting

### Common Issues:

1. **CORS Errors**: Make sure your backend CORS settings include your Vercel domain
2. **API Connection**: Verify `NEXT_PUBLIC_API_URL` is correctly set
3. **Build Failures**: Check that all dependencies are in `package.json`

### Backend CORS Update:

If you get CORS errors, update your Flask app's CORS configuration:

```python
CORS(app, 
     origins=["https://your-vercel-app.vercel.app", "http://localhost:3000"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "Accept"],
     supports_credentials=True,
     expose_headers=["*"]
)
```

## Monitoring

- **Vercel**: Monitor frontend performance in Vercel dashboard
- **Backend**: Use your platform's monitoring tools (Railway, Render, etc.)
- **Logs**: Check both platforms' log systems for debugging

## Updates

To update your application:

1. Push changes to your GitHub repository
2. Vercel will automatically redeploy the frontend
3. Manually redeploy the backend if needed

## Cost Considerations

- **Vercel**: Free tier available for frontend
- **Railway**: Free tier available for backend
- **Render**: Free tier available for backend
- **Heroku**: No free tier anymore, paid plans only 