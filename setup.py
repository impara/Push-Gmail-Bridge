from setuptools import find_packages, setup


setup(
    name="hermes-gmail-bridge",
    version="0.1.0",
    description="Push-based Gmail to Hermes contact inbox bridge.",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.30.0",
        "google-api-python-client>=2.140.0",
        "google-auth>=2.33.0",
        "google-auth-oauthlib>=1.2.0",
        "httpx>=0.27.0",
        "pydantic>=2.8.0",
        "pydantic-settings>=2.4.0",
        "python-dotenv>=1.0.1",
    ],
    extras_require={
        "dev": [
            "pytest>=8.3.0",
            "pytest-asyncio>=0.24.0",
            "respx>=0.21.0",
        ]
    },
)
