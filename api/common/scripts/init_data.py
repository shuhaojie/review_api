#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Initialization data script
Used to insert default LLMProvider data during fresh environment deployment
"""

import os
import django
import sys
from pathlib import Path

# Get current script path
current_script_path = Path(__file__).resolve()
BASE_DIR = current_script_path.parents[3]
# Add project root directory to Python path
sys.path.append(str(BASE_DIR))

# Now we can import env module
from api.common.utils.logger import logger  # noqa

# Set Django environment variables
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.settings.settings")
django.setup()

from api.app.llm.models import LLMProvider  # noqa
from api.app.user.models import Group, User  # noqa
from api.app.llm.models import Prompt  # noqa
from api.settings.config import env  # noqa


def init_llm_providers():
    """
    Initialize LLMProvider default data
    """
    logger.info("Starting to initialize LLMProvider data...")
    if env.DEFAULT_MODEL_NAME.startswith("qwen3"):
        description = "Alibaba qwen3 large model"
    elif env.DEFAULT_MODEL_NAME.startswith("gpt4"):
        description = "OpenAI GPT-4 large model"
    else:
        description = "Large model"
    # Define default LLMProvider data
    default_providers = [
        {
            "name": env.DEFAULT_MODEL_NAME,
            "temperature": env.DEFAULT_TEMPERATURE,
            "frequency_penalty": env.DEFAULT_FREQUENCY_PENALTY,
            "top_p": env.DEFAULT_TOP_P,
            "chunk_length": env.DEFAULT_CHUNK_LENGTH,
            "description": description,
            "url": env.DEFAULT_MODEL_URL,
            "headers": {"Authorization": "Bearer {api_key}"},
            "is_active": True
        }
    ]

    for provider_data in default_providers:
        # Check if active provider already exists
        existing_provider = LLMProvider.objects.filter(
            name=env.DEFAULT_MODEL_NAME,
            is_active=1,
            is_deleted=False).first()

        if existing_provider:
            logger.info(f"{existing_provider.name} is an active model, no need to create, skipping")
        else:
            # Create new provider
            provider = LLMProvider(**provider_data)
            provider.save()
            logger.info(f"Successfully created LLMProvider: {provider.name}")

    logger.info("\nInitialization completed")


# Add a default prompt
def init_prompts():
    """
    Initialize Prompt default data
    """
    logger.info("Starting to initialize Prompt data...")

    # Define default Prompt data
    default_prompts = [
        {
            "name": "Default Prompt",
            "content": 'You are a securities document quality inspector, familiar with regulatory terms such as the "Administrative Measures for Information Disclosure of Publicly Offered Securities Investment Funds".\nTask: Find errors in the document. Do not report false positives. If it\'s not an error, do not display it in the results.',
        }
    ]

    for prompt_data in default_prompts:
        # Check if prompt with the same name already exists
        existing_prompt = Prompt.objects.filter(
            name=prompt_data["name"],
            is_deleted=False).first()

        if existing_prompt:
            logger.info(f"{existing_prompt.name} already exists, no need to create, skipping")
        else:
            # Create new prompt
            prompt = Prompt(**prompt_data)
            prompt.save()
            logger.info(f"Successfully created Prompt: {prompt.name}")

    logger.info("\nInitialization completed")


# Add a [Default Group] group, if the name exists, do not create
def init_groups():
    """
    Initialize Group default data
    """
    logger.info("Starting to initialize Group data...")

    # Define default Group data
    default_groups = [
        {
            "name": "Default Group",
            "description": "Default Group",
        }
    ]

    for group_data in default_groups:
        # Check if group with the same name already exists
        existing_group = Group.objects.filter(
            name=group_data["name"],
            is_deleted=False).first()

        if existing_group:
            logger.info(f"{existing_group.name} already exists, no need to create, skipping")
        else:
            # Create new group
            group = Group(**group_data)
            group.save()
            logger.info(f"Successfully created Group: {group.name}")

    logger.info("\nInitialization completed")


# Create a user named admin with password 1qaz@WSX
def init_admin_user():
    """
    Initialize Admin user
    """
    logger.info("Starting to initialize Admin user...")

    # Check if admin user already exists
    existing_admin = User.objects.filter(
        username="admin",
        is_deleted=False).first()

    if existing_admin:
        logger.info("admin user already exists, no need to create, skipping")
    else:
        # Create new admin user
        admin_user = User.objects.create_user(
            username="admin",
            password="1qaz@WSX",  # Note: This method will automatically encrypt the password
            email="admin@example.com",
            is_staff=True,
            is_superuser=True
        )
        admin_user.save()
        logger.info("Successfully created Admin user: admin")

    logger.info("\nInitialization completed")


if __name__ == "__main__":
    try:
        init_llm_providers()
        init_prompts()
        init_groups()
        init_admin_user()
    except Exception as e:
        logger.error(f"Error occurred during initialization: {str(e)}")
        sys.exit(1)
