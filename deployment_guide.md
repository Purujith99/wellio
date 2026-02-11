# Wellio Deployment Guide

This guide covers the necessary steps to deploy Wellio in a production environment (Streamlit Cloud, Heroku, AWS, or Docker).

## Required Environment Variables

Ensure the following environment variables are set in your deployment environment:

### Core Configuration
- `APP_URL`: The public URL of your application (e.g., `https://wellio-demo.streamlit.app`). Used for OAuth redirects.
- `WELLIO_STORAGE_DIR`: (Optional) Absolute path for persistent session storage. Recommended for Docker deployments.
- `HAARCASCADE_PATH`: (Optional) Path to `haarcascade_frontalface_default.xml` if not in the default search path.

### Supabase (Authentication & Database)
- `SUPABASE_URL`: Your Supabase project URL.
- `SUPABASE_KEY`: Your Supabase Anon/Public Key.

### AI Insights (Groq)
- `GROQ_API_KEY`: Your Groq API key for health explanations and chatbot.

### AWS (S3 Support - Optional)
- `AWS_ACCESS_KEY_ID`: AWS access key.
- `AWS_SECRET_ACCESS_KEY`: AWS secret key.
- `AWS_REGION`: AWS region (e.g., `us-east-1`).
- `AWS_S3_BUCKET`: The name of your S3 bucket for PDF reports.

### Google OAuth (Optional)
- `GOOGLE_CLIENT_ID`: Google OAuth Client ID.
- `GOOGLE_CLIENT_SECRET`: Google OAuth Client Secret.

## Supabase Configuration

To enable Google Auth:
1. Go to **Supabase Dashboard** > **Authentication** > **Providers**.
2. Enable **Google** and enter your Client ID and Secret.
3. In **Redirect URLs**, add `{APP_URL}` (e.g., `https://wellio-demo.streamlit.app`).

## Docker Deployment

1. Build the image:
   ```bash
   docker build -t wellio .
   ```

2. Run the container with persistence:
   ```bash
   docker run -d \
     -p 8501:8501 \
     -v wellio_data:/app/sessions \
     -e WELLIO_STORAGE_DIR=/app/sessions \
     --env-file .env \
     wellio
   ```

## Troubleshooting

- **OpenCV Errors**: Ensure `libgl1-mesa-glx` and `libglib2.0-0` are installed (handled in the provided Dockerfile).
- **OAuth Failures**: Double-check that `APP_URL` matches exactly what is configured in the Google Console and Supabase Dashboard.
