import os
import sys
import glob
import uuid
import requests
import tldextract
import subprocess
import traceback
from typing import List, Union
from urllib.parse import urlparse
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup, Tag, Comment
import praw
import difflib
import re
import json

from langchain.agents import Tool, AgentExecutor, LLMSingleActionAgent, AgentOutputParser
from langchain.prompts import StringPromptTemplate
from langchain.schema import AgentAction, AgentFinish, OutputParserException
from langchain.utilities.tavily_search import TavilySearchAPIWrapper
from langchain.tools.tavily_search import TavilySearchResults
from langchain_community.chat_models import ChatOpenAI
from langchain.tools.base import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain import LLMChain
from langchain_community.callbacks import get_openai_callback

from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()

# Set environment variables
GOOGLE_API_KEY=os.getenv('GOOGLE_API_KEY')
OPENAI_API_KEY=os.getenv('OPENAI_API_KEY')
OPENAI_API_TYPE=os.getenv('OPENAI_API_TYPE')
OPENAI_API_VERSION=os.getenv('OPENAI_API_VERSION')
OPENAI_API_BASE=os.getenv('OPENAI_API_BASE')
TAVILY_API_KEY=os.getenv('TAVILY_API_KE')
LANGCHAIN_TRACING_V2=os.getenv('LANGCHAIN_TRACING_V2')
LANGCHAIN_ENDPOINT=os.getenv('LANGCHAIN_ENDPOINT')
LANGCHAIN_API_KEY=os.getenv('LANGCHAIN_API_KEY')
LOG_DIR=os.getenv('LOG_DIR', '/app/logs/')
SAVE_CONTENT_DIR=os.getenv('SAVE_CONTENT_DIR', '/app/content/')
SAVE_SCREENSHOT_DIR=os.getenv('SAVE_SCREENSHOT_DIR', '/app/screenshots/')
SAVE_LLM_RESPONSE_DIR=os.getenv('SAVE_LLM_RESPONSE_DIR', '/app/results/')
TWITTER_BEARER_TOKEN=os.getenv('TWITTER_BEARER_TOKEN')
REDDIT_CLIENT_ID=os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET=os.getenv('REDDIT_CLIENT_SECRET')
TARGET_URL_FILE=os.getenv('TARGET_URL_FILE')
ANALYSIS_LLM_TYPE=os.getenv('ANALYSIS_LLM_TYPE')

current_time = datetime.now().strftime("%Y%m%dT%H%M%S")

# Function to generate a unique UUID from a URL
def generate_uuid_from_url(url):  
    unique_uuid = uuid.uuid5(uuid.NAMESPACE_URL, url)  
    return unique_uuid  

# Function to check if a new text is similar to existing texts
def is_similar(new_text, extracted_texts, similarity_threshold=0.8):  
    for existing_text in extracted_texts:  
        similarity = difflib.SequenceMatcher(None, new_text, existing_text).ratio()  
        if similarity > similarity_threshold:  
            return True  
    return False  

# Tool classes definition

# Tool to access a URL and obtain status code
class AccessURLTool(BaseTool):
    name = "AccessURL"
    description = "A tool that accesses a URL to obtain a status code. This tool requires a URL as an argument."

    def _run(self, url):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            tld = tldextract.extract(url).suffix
            device = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "screen": {"width": 1920, "height": 1080},
                "viewport": {"width": 1280, "height": 720},
                "device_scale_factor": 1,
                "is_mobile": False,
                "has_touch": False,
                "default_browser_type": "chromium",
                "extra_http_headers": {"Referer": "https://www.google.com/"}
            }
            context = browser.new_context(**device)
            context.set_default_timeout(60000)
            page = context.new_page()
            response = page.goto(url)
            
            base_domain = urlparse(url).netloc
            generated_uuid = generate_uuid_from_url(url)
            content_filename = f"{current_time}_{generated_uuid}_{base_domain}.html"
            screenshot_filename = f"{current_time}_{generated_uuid}_{base_domain}.png"
            
            content = page.content()
            if not os.path.exists(f'{SAVE_CONTENT_DIR}'):
                os.mkdir(f'{SAVE_CONTENT_DIR}')
            with open(f'{SAVE_CONTENT_DIR}/{content_filename}', 'w', encoding='utf-8') as f:
                f.write(content)
            
            if not os.path.exists(f'{SAVE_SCREENSHOT_DIR}'):
                os.mkdir(f'{SAVE_SCREENSHOT_DIR}')
            page.screenshot(path=f'{SAVE_SCREENSHOT_DIR}/{screenshot_filename}', full_page=True)
            
            status_code = response.status
            browser.close()
            return f"Navigating to {url} returned status code {status_code}"

    async def _arun(self, url):
        """Use the AccessURLTool asynchronously."""
        return self._run(url)

# Tool to extract text from HTML content
class ExtractTextTool(BaseTool):
    name = "ExtractText"
    description = "A tool extracts text in the HTML. You must first access the URL using the AccessURL tool before you can use this tool. This tool requires a URL as an argument."

    def _run(self, url):
        unique_uuid = uuid.uuid5(uuid.NAMESPACE_URL, url)
        html_file_list = glob.glob(f'{SAVE_CONTENT_DIR}/*{unique_uuid}*.html')
        if len(html_file_list) <= 0:
            html_file_list = glob.glob(f'{SAVE_CONTENT_DIR}/*{unique_uuid}*.html')
        if len(html_file_list) <= 0:
            return "You must first access the URL using the AccessURL tool before you can use this tool."
        
        html_file = html_file_list[-1]
        with open(html_file, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        soup = BeautifulSoup(html_content, 'lxml')
        for script_or_style in soup(['script', 'style', 'noscript']):
            script_or_style.decompose()
        for comment in soup.findAll(text=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        for tag in soup():
            for attribute in ["style", "onclick", "onmouseover", "onmouseout", "onchange", "onload"]:
                del tag[attribute]
        
        extracted_texts = []
        tags_seen = {}
        for tag in soup.find_all(True):
            parent_id = str(id(tag.parent))
            tag_name = tag.name
            unique_key = f"{parent_id}_{tag_name}"
            if tags_seen.get(unique_key, 0) < 3:
                tags_seen[unique_key] = tags_seen.get(unique_key, 0) + 1
                new_text = next(tag.stripped_strings, "")
                if not is_similar(new_text, extracted_texts):
                    extracted_texts.append(new_text)
        
        return " ".join(extracted_texts)

    async def _arun(self, url):
        """Use the ExtractTextTool asynchronously."""
        return self._run(url)

# Tool to extract hyperlinks from HTML content
class ExtractHyperlinkTool(BaseTool):
    """Tool accesses the URL and extracts the a-tag hyperlink and text pairs in the HTML"""

    name = "ExtractHyperlink"
    description = (
        "A tool extracts a-tag hyperlinks and texts in the HTML. You must first access the URL using the AccessURL tool before you can use this tool. This tool requires a URL as an argument."
    )

    def _run(self, url):
        unique_uuid = uuid.uuid5(uuid.NAMESPACE_URL, url)
        html_file_list = glob.glob(f'{SAVE_CONTENT_DIR}/*{unique_uuid}*.html')
        if len(html_file_list) <= 0:
            html_file_list = glob.glob(f'{SAVE_CONTENT_DIR}/*{unique_uuid}*.html')
            if len(html_file_list) <= 0:
                return "You must first access the URL using the AccessURL tool before you can use this tool."   
        html_file = html_file_list[-1]

        with open(html_file, 'r', encoding='utf-8') as file:  
            html_content = file.read()  
        
        soup = BeautifulSoup(html_content, 'html.parser')  
        
        def find_initial_a_tag_level(tag, current_level=0):  
            if tag.name == 'a' and 'http' in tag.get('href', ''):  
                return current_level  
            child_levels = [find_initial_a_tag_level(child, current_level + 1)   
                            for child in tag.children if isinstance(child, Tag)]  
            if child_levels:  
                return min(child_levels)  
            else:  
                return sys.maxsize
            
        initial_level = find_initial_a_tag_level(soup)
        max_level = initial_level +1 
      
        def extract_a_tags_with_http(tag, current_level=0):  
            if current_level > max_level:  
                return  
            for child in tag.children:  
                if isinstance(child, Tag):  
                    if child.name == 'a' and 'http' in child.get('href', ''):  
                        yield (child.get('href'), child.text.strip())  
                    yield from extract_a_tags_with_http(child, current_level + 1)  
        
        return list(extract_a_tags_with_http(soup))  

    async def _arun(self, url):
        """Use the ExtractHyperlinkTool asynchronously."""
        return self._run(url)

# Tool to retrieve WHOIS information
class RetrieveWHOISTool(BaseTool):
    """Tool to retrieve domain name information from WHOIS."""

    name = "RetrieveWHOIS"
    description = (
        "A tool to retrieve domain name information from WHOIS. This tool requires a domain name as an argument."
    )

    def _run(self, domain_name):
        paylevel_domain_name = tldextract.extract(domain_name).registered_domain
        url = f"https://api.whoisproxy.info/whois/{paylevel_domain_name}"  
        response = requests.get(url)  
        
        if response.status_code == 200:  
            return response.json()['results'] 
        else:  
            return f"Error: {response.status_code}"  

    async def _arun(self, domain_name):
        """Use the WhoisRetrieveTool asynchronously."""
        return self._run(domain_name)

# Tool to retrieve certificate information
class RetrieveCertificateTool(BaseTool):
    """Tool to retrieve certificate information from crt.sh."""

    name = "RetrieveCertificate"
    description = (
        "A tool to retrieve ertificate information from crt.sh. This tool requires a domain name as an argument. Note that only the top 5 results will be retrieved."
    )

    def _run(self, domain):
        url = f"https://crt.sh/?q={domain}&output=json"  
  
        response = requests.get(url)  
        
        if response.ok:  
            certificates = response.json()  
            return certificates[:5]
        else:  
            return "Error fetching certificates information"

    async def _arun(self, domain_name):
        """Use the RetrieveCertificate asynchronously."""
        return self._run(domain_name)

# Tool to retrieve DNS records
class RetrieveDNSRecordTool(BaseTool):
    """Tool to retrieve dns records using the dig command"""

    name = "RetrieveDNSRecord"
    description = (
        "A tool to retrieve dns records using the dig command. This tool requires a domain name as an argument."
    )

    def _run(self, domain_name):
        command = ["dig", "ANY", domain_name, "@8.8.8.8"] 
        result = subprocess.run(command, stdout=subprocess.PIPE, text=True) 
        return result.stdout  

    async def _arun(self, domain_name):
        """Use the RetrieveDNSRecordTool asynchronously."""
        return self._run(domain_name)

# Tool to search X/Twitter
class SearchXTwitterTool(BaseTool):
    """Tool to search and retrieve posts containing keywords from X/Twitter."""

    name = "SearchX/Twitter"
    description = (
        "A tool to search and retrieve posts containing keywords from X/Twitter. This tool requires a search query as an argument. You cannot take a URL as-is as a search query. Note that only the latest top 10 results will be searched."
    )
    max_results = '100'
    tweet_fields = [
        'created_at',
        'id',
        'lang',
        'source',
        'text',
        'conversation_id',
        'entities',
        'public_metrics'
    ]

    user_fields = [
            'created_at',
            'description',
            'entities',
            'id',
            'name',
            'profile_image_url',
            'public_metrics',
            'url',
            'username',
            'verified'
    ]

    def _run(self, search_query):
        url = f'https://api.twitter.com/2/tweets/search/recent?query={search_query}&max_results={self.max_results}&tweet.fields={",".join(self.tweet_fields)}&user.fields={",".join(self.user_fields)}'
        headers = {
        'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}',
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:  
            data = response.json()
            return data
        else:  
            return f'Error: Unable to fetch data, status code {response.status_code}' 

    async def _arun(self, domain_name):
        """Use the SearchXTwitterTool asynchronously."""
        return self._run(domain_name)

# Tool to search Reddit
class SearchRedditTool(BaseTool):
    """Tool to search and retrieve posts containing keywords from Reddit."""

    name = "SearchReddit"
    description = (
        "A tool to search and retrieve posts containing keywords from Reddit. This tool requires a search query as an argument. You cannot take a URL as-is as a search query. Note that only the top five related posts and the top five comments associated with them will be searched."
    )
    
    reddit = praw.Reddit(  
        client_id=REDDIT_CLIENT_ID,  
        client_secret=REDDIT_CLIENT_SECRET,  
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'  
    )  

    def _run(self, search_query):
        results = list()  
        for submission in self.reddit.subreddit("all").search(search_query, limit=5):
            dic = {
                    'title':f'{submission.title}',
                    'subreddit':f'{submission.subreddit}',
                    'url':f'{submission.url}',
                    'selftext':f'{submission.selftext}'
                }
            comments = list()
            index = 0
            for index, comment in enumerate(submission.comments):
                try:
                    if index >= 5:
                        break
                    comments.append(comment.body.strip())
                except:
                    continue
            dic['comments'] = comments
            results.append(dic)
        return results

    async def _arun(self, domain_name):
        """Use the SearchXRedditTool asynchronously."""
        return self._run(domain_name)

# Custom prompt template for the agent
class CustomPromptTemplate(StringPromptTemplate):
    template: str
    tools: List[Tool]

    def format(self, **kwargs) -> str:
        intermediate_steps = kwargs.pop("intermediate_steps")
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\nObservation: {observation}\nThought: "
        kwargs["agent_scratchpad"] = thoughts
        kwargs["tools"] = "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools])
        kwargs["tool_names"] = ", ".join([tool.name for tool in self.tools])
        return self.template.format(**kwargs)

# Custom output parser for the agent
class CustomOutputParser(AgentOutputParser):
    def parse(self, llm_output: str) -> Union[AgentAction, AgentFinish]:
        if "Final Answer:" in llm_output:
            return AgentFinish(
                return_values={"output": llm_output.split("Final Answer:")[-1].strip()},
                log=llm_output,
            )
        regex = r"Action\s*\d*\s*:(.*?)\nAction\s*\d*\s*Input\s*\d*\s*:[\s]*(.*)"
        match = re.search(regex, llm_output, re.DOTALL)
        if not match:
            raise OutputParserException(f"Could not parse LLM output: `{llm_output}`")
        action = match.group(1).strip()
        action_input = match.group(2)
        return AgentAction(tool=action, tool_input=action_input.strip(" ").strip('"'), log=llm_output)

def main():
    template = """
    I want you to act as a professional scam website detection expert. You are tasked with analyzing the content of URLs given to you to determine if the URL is a scam website or not. Scam websites have the following characteristics.
    1. Unusually low prices and claims of free.
    2. Claims to be able to get an amount of money that is generally not possible.
    3. Texts that target human psychological weaknesses exist on websites.
    4. Information on non-existent companies.
    5. Handling different products from common e-commerce websites.
    6. Inquiry phone number and email address are not appropriate for business use.
    7. Privacy of customer information notation is ambiguous.
    8. Payment methods are not common and are unusual.
    9. The information listed has not been updated.
    You can access the following tools to help you answer the question:
    {tools}
    Please follow the format below when answering the questions:
    Question: the question you must answer
    Thought: you should always think about what to do
    Action: the action to take, should be one of [{tool_names}]
    Action Input: the input to the action
    Observation: the result of the action
    ... (You can repeat this Thought/Action/Action Input/Observation N times to derive your answer.)
    Thought: I now know the final answer
    Final Answer: the final answer to the original question
    You are to derive the Final Answer based on no more than ten actions. To do so, you need to analyze efficiently. Be sure to say I now know the final answer when you know the answer.
    After the Final Answer is determined, output the analysis results in JSON format according to the following key:
    - result : True or False (result of URL scam determination)
    - scam_type : Fake shopping site (specific type of scam)
    - reason : Please logically state the basis for your decision using the characteristics of the scam website shared
    Begin! Please note that the URLs to be analyzed are legitimate sites!
    Question: {input}
    {agent_scratchpad}
    """

    if ANALYSIS_LLM_TYPE == 'gemini-pro':
        llm = ChatGoogleGenerativeAI(model=ANALYSIS_LLM_TYPE, convert_system_message_to_human=False)
    elif ANALYSIS_LLM_TYPE == 'gpt-4':
        llm = ChatOpenAI(model=ANALYSIS_LLM_TYPE, model_kwargs={"deployment_id":ANALYSIS_LLM_TYPE})
    elif ANALYSIS_LLM_TYPE == 'gpt-3.5':
        llm = ChatOpenAI(model=ANALYSIS_LLM_TYPE, model_kwargs={"deployment_id":ANALYSIS_LLM_TYPE})
    else:
        print('Please set proper llm_type: gemini-pro, gpt-4 or gpt-3.5')
        sys.exit()

    search = TavilySearchAPIWrapper()
    tavily_tool = TavilySearchResults(api_wrapper=search)
    whois_tool = RetrieveWHOISTool()
    access_tool = AccessURLTool()
    text_tool = ExtractTextTool()
    hyperlink_tool = ExtractHyperlinkTool()
    certificate_tool = RetrieveCertificateTool()
    dnsrecord_tool = RetrieveDNSRecordTool()
    xsearch_tool = SearchXTwitterTool()
    redditsearch_tool = SearchRedditTool()
    
    tools = [
        Tool(
        name=access_tool.name,
        func=access_tool.run,
        coroutine=access_tool.arun,
        description=access_tool.description
        ),
        Tool(
        name=text_tool.name,
        func=text_tool.run,
        coroutine=text_tool.arun,
        description=text_tool.description
        ),
        Tool(
            name=hyperlink_tool.name,
            func=hyperlink_tool.run,
            coroutine=hyperlink_tool.arun,
            description=hyperlink_tool.description
        ),
        Tool(
            name="GetSearchResult",
            func=tavily_tool.run,
            coroutine=tavily_tool.arun,
            description="A tool to retrieve search results from a search engine. This tool requires a search query as an argument. You cannot take a URL as-is as a search query."
        ),
        Tool(
            name=whois_tool.name,
            func=whois_tool.run,
            coroutine=whois_tool.arun,
            description=whois_tool.description
        ),
        Tool(
            name=certificate_tool.name,
            func=certificate_tool.run,
            coroutine=certificate_tool.arun,
            description=certificate_tool.description
        ),
        Tool(
            name=dnsrecord_tool.name,
            func=dnsrecord_tool.run,
            coroutine=dnsrecord_tool.arun,
            description=dnsrecord_tool.description
        ),
        Tool(
            name=xsearch_tool.name,
            func=xsearch_tool.run,
            coroutine=xsearch_tool.arun,
            description=xsearch_tool.description
        ),
        Tool(
            name=redditsearch_tool.name,
            func=redditsearch_tool.run,
            coroutine=redditsearch_tool.arun,
            description=redditsearch_tool.description
        )
    ]

    prompt = CustomPromptTemplate(template=template, tools=tools, input_variables=["input", "intermediate_steps"])
    llm_chain = LLMChain(llm=llm, prompt=prompt)
    output_parser = CustomOutputParser()
    tool_names = [tool.name for tool in tools]
    agent = LLMSingleActionAgent(llm_chain=llm_chain, output_parser=output_parser, stop=["\nObservation:"], allowed_tools=tool_names)
    agent_executor = AgentExecutor.from_agent_and_tools(agent=agent, tools=tools, verbose=True)
    
    with open(TARGET_URL_FILE, 'r') as f:
        url_list = [line.strip() for line in f]
    
    for url in url_list:
        try:
            base_domain = urlparse(url).netloc
            generated_uuid = generate_uuid_from_url(url)
            filename = f"{current_time}_{generated_uuid}_{base_domain}"
            sys.stdout = open(f'{LOG_DIR}/{filename}.log', 'a+')
            print(url, base_domain)

            if ANALYSIS_LLM_TYPE in ['gpt-4', 'gpt-3.5']:
                with get_openai_callback() as cb:
                    result_raw = agent_executor.run(f"Please analyze this URL {url}.")
                try:
                    # Find the start and end of the JSON part
                    start = result_raw.find('{')
                    end = result_raw.rfind('}') + 1

                    # Extract the JSON string
                    result = json.loads(result_raw[start:end])
                except:
                    result = result_raw
                
                result_dict = {
                    'target_url': url,
                    'analysis_llm': ANALYSIS_LLM_TYPE,
                    'llm_response':result,
                    'total_tokens': cb.total_tokens,
                    'prompt_tokens': cb.prompt_tokens,
                    'completion_tokens': cb.completion_tokens,
                    'total_cost': cb.total_cost
                    }
                print(result)
                print(f"Total Tokens: {cb.total_tokens}")
                print(f"Prompt Tokens: {cb.prompt_tokens}")
                print(f"Completion Tokens: {cb.completion_tokens}")
                print(f"Total Cost (USD): ${cb.total_cost}")
            else:
                result_raw = agent_executor.run(f"Please analyze this URL {url}.")
                try:
                    # Find the start and end of the JSON part
                    start = result_raw.find('{')
                    end = result_raw.rfind('}') + 1

                    # Extract the JSON string
                    result = json.loads(result_raw[start:end])
                except:
                    result = result_raw

                result_dict = {
                    'target_url': url,
                    'analysis_llm': ANALYSIS_LLM_TYPE,
                    'llm_response':result
                }
                print(result)
            with open(f'{SAVE_LLM_RESPONSE_DIR}/{filename}.json', 'w') as file:
                json.dump(result_dict, file, indent=4)
        except:
            print(traceback.format_exc())
            continue

if __name__ == '__main__':
    main()