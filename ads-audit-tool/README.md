# Ads Audit Tool

Automated paid advertising audit and optimization platform for Google Ads.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- Google Cloud project with OAuth 2.0 credentials and Google Ads API enabled

## Quick Start

```bash
cp backend/.env.example backend/.env
# Fill in your Google OAuth and Ads API credentials in backend/.env
docker-compose up
```

The backend API will be available at `http://localhost:8000` and the frontend at `http://localhost:3000`.

## Railway Deployment

To deploy on Railway, connect your repository and set the required environment variables in the Railway dashboard. See the [Railway documentation](https://docs.railway.app/) for details.
