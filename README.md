# ScamFerret - Source Code and Dataset
# Artifact Description

This is the implementation code, dataset, and evaluation results for the paper "ScamFerret: Detecting Scam Websites Autonomously with Large Language Models" accepted to appear at DIMVA 2025.

**In September 2025, the system was further improved, with support added for several additional types of scams, and new datasets and evaluation results were included in expanded_dataset, expanded_evaluation and expanded_reasoning.**

## Directory Tree

<pre>
.
├── README.md
├── dataset
│   ├── legitimate_websites
│   │   ├── cryptocurrency
│   │   │   ├── sample_screenshot
│   │   │   │   └── ...
│   │   │   ├── toppage_html
│   │   │   │   └── ...
│   │   │   └── groundtruth_url.txt
│   │   ├── investment
│   │   │   └── ...
│   │   ├── online_shopping_english
│   │   │   └── ...
│   │   ├── online_shopping_german
│   │   │   └── ...
│   │   ├── online_shopping_japanese
│   │   │   └── ...
│   │   └── technical_support
│   │       └── ...
│   └── scam_websites
│       ├── cryptocurrency
│       │   ├── sample_screenshot
│       │   │   └── ...
│       │   ├── toppage_html
│       │   │   └── ...
│       │   └── groundtruth_url.txt
│       ├── investment
│       │   └── ...
│       ├── online_shopping_english
│       │   └── ...
│       ├── online_shopping_german
│       │   └── ...
│       ├── online_shopping_japanese
│       │   └── ...
│       └── technical_support
│           └── ...
├── dataset_training
│   ├── legitimate_websites
│   │   ├── cryptocurrency
│   │   │   ├── toppage_html
│   │   │   │   └── ...
│   │   │   └── groundtruth_url.txt
│   │   ├── investment
│   │   │   └── ...
│   │   ├── online_shopping_english
│   │   │   └── ...
│   │   └── technical_support
│   │       └── ...
│   └── scam_websites
│       ├── cryptocurrency
│       │   ├── toppage_html
│       │   │   └── ...
│       │   └── groundtruth_url.txt
│       ├── investment
│       │   └── ...
│       ├── online_shopping_english
│       │   └── ...
│       └── technical_support
│           └── ...
├── evaluation
│   ├── classification_accuracy.ipynb
│   ├── geminipro_results
│   │   ├── legitimate_websites
│   │   │   ├── cryptocurrency
│   │   │   ├── investment
│   │   │   ├── online_shopping_english
│   │   │   ├── online_shopping_german
│   │   │   ├── online_shopping_japanese
│   │   │   └── technical_support
│   │   └── scam_websites
│   │       ├── cryptocurrency
│   │       ├── investment
│   │       ├── online_shopping_english
│   │       ├── online_shopping_german
│   │       ├── online_shopping_japanese
│   │       └── technical_support
│   ├── gpt-3.5_results
│   │   ├── legitimate_websites
│   │   │   └── ...
│   │   └── scam_websites
│   │       └── ...
│   ├── gpt-4_results
│   │   ├── legitimate_websites
│   │   │   └── ...
│   │   └── scam_websites
│   │       └── ...
│   └── information_used.ipynb
├── expanded_dataset
│   ├── emerging_scam_websites
│   │   └── ...
│   ├── legitimate_websites
│   │   └── ...
│   └── scam_websites
│       └── ...
├── expanded_evaluation
│   ├── gpt-4.1_results
│   │   ├── emerging_scam_websites
│   │   │   └── ...
│   │   ├── legitimate_websites
│   │   │   └── ...
│   │   └── scam_websites
│   │       └── ...
│   ├── gpt-4o-mini_results
│   │   └── ...
│   ├── llama3.1_results
│   │   └── ...
│   ├── llama3.3_results
│   │   └── ...
│   ├── llama4_results
│   │   └── ...
│   └── o3-mini_results
│       └── ...
├── expanded_reasoning
│   ├── gpt-4.1_results
│   │   └── ...
│   ├── gpt-4o-mini_results
│   │   └── ...
│   ├── llama3.1_results
│   │   └── ...
│   ├── llama3.3_results
│   │   └── ...
│   ├── llama4_results
│   │   └── ...
│   └── o3-mini_results
│       └── ...
└── prompt
│   ├── prompt_template.txt
│   └── single-turn_prompt.txt
└── system
    ├── content
    │   └──...
    ├── logs
    │   └── ...
    ├── results
    │   └──...
    ├── screenshot
    │   └── ...
    ├── .env
    ├── app.py
    ├── docker-compose.yml
    ├── Dockerfile
    ├── requirements.txt
    └── sample_urls.txt

</pre>


## Directory Descriptions

- **dataset/**: Ground-truth dataset for evaluating the proposed system. The dataset contains 1,200 scam websites and 1,200 legitimate websites, with 200 websites in each of six categories: online shopping (English, German, and Japanese), technical support, cryptocurrency, and investment.
  - **legitimate_websites/**: Contains directories related to different types of legitimate websites.
    - **cryptocurrency/**:
      - `sample_screenshot/`: 20 screenshots for each type of scam and language (limited due to file size).
      - `toppage_html/`: Directory for top page HTML files.
      - `groundtruth_url.txt`: Contains ground-truth URLs.
    - **investment/**, **online_shopping_english/**, **online_shopping_german/**, **online_shopping_japanese/**, **technical_support/**: Follow the same structure as `cryptocurrency/`, containing respective data and resources.
  - **scam_websites/**: Contains directories related to different types of scam websites.
    - **cryptocurrency/**,**investment/**, **online_shopping_english/**, **online_shopping_german/**, **online_shopping_japanese/**, **technical_support/**: Follow the same structure as `legitimate_websites/cryptocurrency/`, containing respective data and resources.

- **dataset_training/**: Training dataset for two conventional systems. The dataset comprises 800 English scam websites and 800 English legitimate websites, with 200 sites in each category: online shopping, technical support, cryptocurrency, and investment.
  - **legitimate_websites/**: Contains directories related to different types of legitimate websites.
    - **cryptocurrency/**:
      - `toppage_html/`: Directory for top page HTML files.
      - `groundtruth_url.txt`: Contains ground-truth URLs.
    - **investment/**, **online_shopping_english/**, **technical_support/**: Follow the same structure as `cryptocurrency/`, containing respective data and resources.
  - **scam_websites/**: Contains directories related to different types of scam websites.
    - **cryptocurrency/**,**investment/**, **online_shopping_english/**, **technical_support/**: Follow the same structure as `legitimate_websites/cryptocurrency/`, containing respective data and resources.

- **evaluation/**: Evaluation results of the proposed system using the ground-truth dataset.
  - **geminipro_results/**: Experimental results with Gemini Pro for LLM.
    - **legitimate_websites/**: Contains directories related to different types of legitimate websites.
      - **cryptocurrency/**:
        - `[DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
      - **investment/**, **online_shopping_english/**, **online_shopping_german/**, **online_shopping_japanese/**, **technical_support/**: Follow the same structure as `cryptocurrency/`, containing respective data.
    - **scam_websites/**: Contains directories related to different types of scam websites.
      - **cryptocurrency/**,**investment/**, **online_shopping_english/**, **online_shopping_german/**, **online_shopping_japanese/**, **technical_support/**: Follow the same structure as `legitimate_websites/cryptocurrency/`, containing respective data.
  - **gpt-3.5_results/**: Experimental results with GPT-3.5 for LLM.
    - **legitimate_websites/**: Contains directories related to different types of legitimate websites.
      - **cryptocurrency/**,**investment/**, **online_shopping_english/**, **online_shopping_german/**, **online_shopping_japanese/**, **technical_support/**: Follow the same structure as `geminipro_results/legitimate_websites/cryptocurrency/`, containing respective data.
    - **scam_websites/**: Contains directories related to different types of scam websites.
      - **cryptocurrency/**,**investment/**, **online_shopping_english/**, **online_shopping_german/**, **online_shopping_japanese/**, **technical_support/**: Follow the same structure as `geminipro_results/legitimate_websites/cryptocurrency/`, containing respective data.
  - **gpt-4_results/**: Experimental results with GPT-4 for LLM.
    - **legitimate_websites/**: Contains directories related to different types of legitimate websites.
      - **cryptocurrency/**,**investment/**, **online_shopping_english/**, **online_shopping_german/**, **online_shopping_japanese/**, **technical_support/**: Follow the same structure as `geminipro_results/legitimate_websites/cryptocurrency/`, containing respective data.
    - **scam_websites/**: Contains directories related to different types of scam websites.
      - **cryptocurrency/**,**investment/**, **online_shopping_english/**, **online_shopping_german/**, **online_shopping_japanese/**, **technical_support/**: Follow the same structure as `geminipro_results/legitimate_websites/cryptocurrency/`, containing respective data.

- **expanded_dataset/**: Ground-truth dataset for evaluating the proposed system **(updated in September 2025)**. The dataset contains 2,780 scam websites and 2,000 legitimate websites, spanning eleven scam types and seven languages. The multi-type subset covers four major scam types (online shopping, technical support, cryptocurrency, investment) and seven emerging scam types (gaming, gambling, porn, pharmacy, transportation, survey, weight-loss) in English, with a total of 1,580 scam and 800 legitimate websites. The multilingual subset focuses on online shopping across English, Dutch, French, German, Italian, Japanese, and Spanish, consisting of 1,400 scam and 1,400 legitimate websites.
  - **emerging_scam_websites/**: Contains directories related to different types of emerging scam websites.
    - `gambling_groundtruth_url.txt`
    - `gaming_groundtruth_url.txt`
    - `pharmacy_groundtruth_url.txt`
    - `porn_groundtruth_url.txt`
    - `survey_groundtruth_url.txt`
    - `transportation_groundtruth_url.txt`
    - `weightloss_groundtruth_url.txt`
  - **legitimate_websites/**: Contains directories related to different types of legitimate websites.
    - `cryptocurrency_groundtruth_url.txt`
    - `investment_groundtruth_url.txt`
    - `online_shopping_dutch_groundtruth_url.txt`
    - `online_shopping_english_groundtruth_url.txt`
    - `online_shopping_french_groundtruth_url.txt`
    - `online_shopping_german_groundtruth_url.txt`
    - `online_shopping_italian_groundtruth_url.txt`
    - `online_shopping_japanese_groundtruth_url.txt`
    - `online_shopping_spanish_groundtruth_url.txt`
    - `technical_support_groundtruth_url.txt`
  - **scam_websites/**: Contains directories related to different types of scam websites.
    - `cryptocurrency_groundtruth_url.txt`
    - `investment_groundtruth_url.txt`
    - `online_shopping_dutch_groundtruth_url.txt`
    - `online_shopping_english_groundtruth_url.txt`
    - `online_shopping_french_groundtruth_url.txt`
    - `online_shopping_german_groundtruth_url.txt`
    - `online_shopping_italian_groundtruth_url.txt`
    - `online_shopping_japanese_groundtruth_url.txt`
    - `online_shopping_spanish_groundtruth_url.txt`
    - `technical_support_groundtruth_url.txt`

- **expanded_evaluation/**: Evaluation results of the proposed system using the expanded ground-truth dataset **(updated in September 2025)**.
  - **gpt-4.1_results/**: Experimental results with GPT-4.1 for LLM.
    - **emering_scam_websites/**: Contains directories related to different types of emerging scam websites.
        - **gambling/**:
          - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
        - **gaming/**, **pharmacy/**, **porn/**, **survey/**, **transportation/**, **weightloss/**: Follow the same structure as `gambling/`, containing respective data.
    - **legitimate_websites/**: Contains directories related to different types of legitimate websites.
      - **cryptocurrency/**:
        - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
      - **investment/**, **online_shopping_dutch/**, **online_shopping_english/**, **online_shopping_french/**, **online_shopping_german/**, **online_shopping_italian/**, **online_shopping_japanese/**, **online_shopping_spanish/**, **technical_support/**: Follow the same structure as `cryptocurrency/`, containing respective data.
    - **scam_websites/**: Contains directories related to different types of legitimate websites.
      - **cryptocurrency/**:
        - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
      - **investment/**, **online_shopping_dutch/**, **online_shopping_english/**, **online_shopping_french/**, **online_shopping_german/**, **online_shopping_italian/**, **online_shopping_japanese/**, **online_shopping_spanish/**, **technical_support/**: Follow the same structure as `cryptocurrency/`, containing respective data.
  - **gpt-4o-mini_results/**: Experimental results with GPT-4o-mini for LLM.
    - **emering_scam_websites/**: Contains directories related to different types of emerging scam websites.
        - **gambling/**:
          - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
        - **gaming/**, **pharmacy/**, **porn/**, **survey/**, **transportation/**, **weightloss/**: Follow the same structure as `gambling/`, containing respective data.
    - **legitimate_websites/**: Contains directories related to different types of legitimate websites.
      - **cryptocurrency/**:
        - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
      - **investment/**, **online_shopping_dutch/**, **online_shopping_english/**, **online_shopping_french/**, **online_shopping_german/**, **online_shopping_italian/**, **online_shopping_japanese/**, **online_shopping_spanish/**, **technical_support/**: Follow the same structure as `cryptocurrency/`, containing respective data.
    - **scam_websites/**: Contains directories related to different types of legitimate websites.
      - **cryptocurrency/**:
        - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
      - **investment/**, **online_shopping_dutch/**, **online_shopping_english/**, **online_shopping_french/**, **online_shopping_german/**, **online_shopping_italian/**, **online_shopping_japanese/**, **online_shopping_spanish/**, **technical_support/**: Follow the same structure as `cryptocurrency/`, containing respective data.
  - **llama3.1_results/**: Experimental results with Llama 3.1 for LLM.
    - **emering_scam_websites/**: Contains directories related to different types of emerging scam websites.
        - **gambling/**:
          - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
        - **gaming/**, **pharmacy/**, **porn/**, **survey/**, **transportation/**, **weightloss/**: Follow the same structure as `gambling/`, containing respective data.
    - **legitimate_websites/**: Contains directories related to different types of legitimate websites.
      - **cryptocurrency/**:
        - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
      - **investment/**, **online_shopping_dutch/**, **online_shopping_english/**, **online_shopping_french/**, **online_shopping_german/**, **online_shopping_italian/**, **online_shopping_japanese/**, **online_shopping_spanish/**, **technical_support/**: Follow the same structure as `cryptocurrency/`, containing respective data.
    - **scam_websites/**: Contains directories related to different types of legitimate websites.
      - **cryptocurrency/**:
        - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
      - **investment/**, **online_shopping_dutch/**, **online_shopping_english/**, **online_shopping_french/**, **online_shopping_german/**, **online_shopping_italian/**, **online_shopping_japanese/**, **online_shopping_spanish/**, **technical_support/**: Follow the same structure as `cryptocurrency/`, containing respective data.
  - **llama3.3_results/**: Experimental results with Llama 3.3 for LLM.
    - **emering_scam_websites/**: Contains directories related to different types of emerging scam websites.
        - **gambling/**:
          - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
        - **gaming/**, **pharmacy/**, **porn/**, **survey/**, **transportation/**, **weightloss/**: Follow the same structure as `gambling/`, containing respective data.
    - **legitimate_websites/**: Contains directories related to different types of legitimate websites.
      - **cryptocurrency/**:
        - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
      - **investment/**, **online_shopping_dutch/**, **online_shopping_english/**, **online_shopping_french/**, **online_shopping_german/**, **online_shopping_italian/**, **online_shopping_japanese/**, **online_shopping_spanish/**, **technical_support/**: Follow the same structure as `cryptocurrency/`, containing respective data.
    - **scam_websites/**: Contains directories related to different types of legitimate websites.
      - **cryptocurrency/**:
        - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
      - **investment/**, **online_shopping_dutch/**, **online_shopping_english/**, **online_shopping_french/**, **online_shopping_german/**, **online_shopping_italian/**, **online_shopping_japanese/**, **online_shopping_spanish/**, **technical_support/**: Follow the same structure as `cryptocurrency/`, containing respective data.
  - **llama4_results/**: Experimental results with Llama 4 for LLM.
    - **emering_scam_websites/**: Contains directories related to different types of emerging scam websites.
        - **gambling/**:
          - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
        - **gaming/**, **pharmacy/**, **porn/**, **survey/**, **transportation/**, **weightloss/**: Follow the same structure as `gambling/`, containing respective data.
    - **legitimate_websites/**: Contains directories related to different types of legitimate websites.
      - **cryptocurrency/**:
        - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
      - **investment/**, **online_shopping_dutch/**, **online_shopping_english/**, **online_shopping_french/**, **online_shopping_german/**, **online_shopping_italian/**, **online_shopping_japanese/**, **online_shopping_spanish/**, **technical_support/**: Follow the same structure as `cryptocurrency/`, containing respective data.
    - **scam_websites/**: Contains directories related to different types of legitimate websites.
      - **cryptocurrency/**:
        - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
      - **investment/**, **online_shopping_dutch/**, **online_shopping_english/**, **online_shopping_french/**, **online_shopping_german/**, **online_shopping_italian/**, **online_shopping_japanese/**, **online_shopping_spanish/**, **technical_support/**: Follow the same structure as `cryptocurrency/`, containing respective data.
  - **o3-mini_results/**: Experimental results with o3-mini for LLM.
    - **emering_scam_websites/**: Contains directories related to different types of emerging scam websites.
        - **gambling/**:
          - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
        - **gaming/**, **pharmacy/**, **porn/**, **survey/**, **transportation/**, **weightloss/**: Follow the same structure as `gambling/`, containing respective data.
    - **legitimate_websites/**: Contains directories related to different types of legitimate websites.
      - **cryptocurrency/**:
        - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
      - **investment/**, **online_shopping_dutch/**, **online_shopping_english/**, **online_shopping_french/**, **online_shopping_german/**, **online_shopping_italian/**, **online_shopping_japanese/**, **online_shopping_spanish/**, **technical_support/**: Follow the same structure as `cryptocurrency/`, containing respective data.
    - **scam_websites/**: Contains directories related to different types of legitimate websites.
      - **cryptocurrency/**:
        - `[UUID_DomainName].json`: Each JSON file contains the analysis results for the specified domain name.
      - **investment/**, **online_shopping_dutch/**, **online_shopping_english/**, **online_shopping_french/**, **online_shopping_german/**, **online_shopping_italian/**, **online_shopping_japanese/**, **online_shopping_spanish/**, **technical_support/**: Follow the same structure as `cryptocurrency/`, containing respective data.

- **expanded_reasoning/**: Contains the results of reasoning quality analysis for the proposed system using the expanded ground-truth dataset **(updated in September 2025)**. For each website, the system's outputs are evaluated not only for classification correctness but also for the quality, logical consistency, and evidential support of the explanations and justifications provided by the models. This directory includes experiment-level summaries and instance-level scores reflecting criteria such as logical consistency, evidence-based reasoning, and compliance with required feature coverage, enabling detailed assessment of the interpretability and transparency of decisions.
  - **gpt-4.1_results/**: Experimental results of reasoning and justification generation using GPT-4.1.
    - `legitimate_cryptocurrency.json`: Each JSON entry records the model's verdict, the structured rationale text, and corresponding quality scores (e.g., logical consistency, evidence-based grounding, feature compliance).
  - **gpt-4o-mini_results/**: Experimental results with GPT-4o-mini for LLM. Follow the same structure as `gpt-4.1_results/`, containing respective data.
  - **llama3.1_results/**: Experimental results with Llama 3.1 for LLM. Follow the same structure as `gpt-4.1_results/`, containing respective data.
  - **llama3.3_results/**: Experimental results with Llama 3.3 for LLM. Follow the same structure as `gpt-4.1_results/`, containing respective data.
  - **llama4_results/**: Experimental results with Llama 4 for LLM. Follow the same structure as `gpt-4.1_results/`, containing respective data.
  - **o3-mini_results/**: Experimental results with o3-mini for LLM. Follow the same structure as `gpt-4.1_results/`, containing respective data.

- **prompt/**: List of full prompts used in the paper.
  - `prompt_template.txt`: Prompt template used for analysis of scam websites in the proposed system **(updated in September 2025)**.
  - `single-turn_prompt.txt`: Prompt used in the system for comparative evaluation.

- **system/**: Source code for the proposed system in the paper.
  - **content/**: The HTML content that the system saves when analyzing scam websites.
  - **logs/**: The logs from the execution of the proposed system.
  - **results/**: The results output by the proposed system.
  - **screenshots/**: The screenshots that the proposed system saves when analyzing scam websites.
  - `.env`: This .env file needs to be set with API keys, etc **(updated in September 2025)**.
  - `app.py`: Code that includes the processing that is the core of the system **(updated in September 2025)**.
  - `docker-compose.yml`: Docker compose configuration file.
  - `Dockerfile`: Docker configuration file.
  - `requirements.txt`: File specifying python's dependent libraries **(updated in September 2025)**.
  - `sample_urls.txt`: List of sample URLs for use in the proposed system input.

- **README.md**: This readme file.


## Project Setup and Execution

This project implements the proposed system using Azure OpenAI Service and LangChain

### 1. Navigate to the system directory
Before starting the setup process, navigate to the system directory in your terminal:

```
cd /path/to/system
```

Replace `/path/to/system` with the actual path to your project's system directory.

### 2. Create a .env file

Create a .env file in the project's root directory with the following content:

```
LOG_DIR="/app/logs/"
SAVE_CONTENT_DIR="/app/content"
SAVE_SCREENSHOT_DIR="/app/screenshots"
SAVE_LLM_RESPONSE_DIR="/app/results"
GOOGLE_API_KEY="xxxxxxxxxxxxxxx"
OPENAI_API_KEY="xxxxxxxxxxxxxxx"
OPENAI_API_TYPE="azure"
OPENAI_API_VERSION="2023-12-01-preview"
OPENAI_API_BASE="https://xxxxxxxxxxxxxxx.openai.azure.com/"
TAVILY_API_KEY="xxxxxxxxxxxxxxx"
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY="xxxxxxxxxxxxxxx"
TWITTER_BEARER_TOKEN="xxxxxxxxxxxxxxx"
TWITTER_BEARER_TOKEN_FILE=""
REDDIT_CLIENT_ID="xxxxxxxxxxxxxxx"
REDDIT_CLIENT_SECRET="xxxxxxxxxxxxxxx"
REDDIT_API_FILE="xxxxxxxxxxxxxxx"
TARGET_URL_FILE="./sample_urls.txt"
ANALYSIS_LLM_TYPE="gpt-4.1"
DATABRICKS_HOST="xxxxxxxxxxxxxxx"
DATABRICKS_TOKEN="xxxxxxxxxxxxxxx"
DATABRICKS_ENDPOINT="xxxxxxxxxxxxxxx"
```

Note: These API keys are sensitive information. Replace them with your own API keys.

### 3. Build the Docker image

Navigate to the project's root directory in your terminal and run the following command to build the Docker image:

```
docker compose build
```

### 4. Start the application

After the build is complete, start the application with the following command:

```
docker compose up -d
```

The `-d` option runs the container in detached mode, starting it in the background.

### 5. Stop the application

To stop the application, run:

```
docker compose down
```

This command stops and removes the containers created by docker compose up.
By following these steps, you can easily start and stop the application using Docker.


## Reference
Please consider citing our paper:
```
@inproceedings{nakano25dimva,
  author       = {Hiroki Nakano and
                  Takashi Koide and
                  Daiki Chiba},
  title        = {ScamFerret: Detecting Scam Websites Autonomously with Large Language Models},
  booktitle    = {Detection of Intrusions and Malware, and Vulnerability Assessment
                  - 22nd International Conference, {DIMVA} 2025, Graz, Austria, July
                  9-11, 2025, Proceedings},
  publisher    = {Springer},
  year         = {2025},
}
```