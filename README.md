# FYS Chatbot

This repository contains:
- A **frontend** (in `frontend/`) with a static HTML/JS/CSS interface. Host this on GitHub Pages.
- A **backend** (in `backend/`) with AWS Lambda code to handle requests and call OpenAI.

## Frontend (GitHub Pages Setup)

1. Place the contents of `frontend/` in your repository.
2. In GitHub, go to **Settings > Pages** and enable GitHub Pages from the `main` branch (or `gh-pages` branch).
3. Wait a few minutes. Your site will be available at `https://yourusername.github.io/yourrepo/`.

**Remember:** Update `script.js` with your actual API Gateway endpoint and API key once you set up the backend.

## Backend (AWS Lambda + API Gateway)

1. Set up a Lambda function in AWS:
   - Python 3.10 runtime.
   - Upload `lambda_function.py`.
   - Set `OPENAI_API_KEY` as an environment variable in Lambda.
   - Install dependencies listed in `requirements.txt` by creating a deployment package or using a Lambda layer.

2. Create an API Gateway (HTTP API or REST API):
   - Integrate it with your Lambda function.
   - Add an API key in API Gateway.
   - Configure usage plans and associate your API with that plan.
   - Secure your endpoint so that `x-api-key: YOUR_API_KEY_HERE` is required.

3. Update `script.js` in the frontend with:
   - `API_URL = "https://your-api-id.execute-api.your-region.amazonaws.com/prod"`
   - `x-api-key: YOUR_API_KEY_HERE`

4. After deployment, test by visiting your GitHub Pages URL and interacting with the chatbot.

## Notes

- The chatbot flow:
  - User opens GitHub Pages site.
  - Frontend asks for name, then shows main menu buttons.
  - User chooses, types career/college when asked, or picks majors from buttons.
  - All requests go to AWS API Gateway + Lambda with `x-api-key` header.
  - Lambda calls OpenAI, returns responses.

- Keep your API keys secure. The frontend API key is exposed to users, so consider rate limits or a less sensitive key.

