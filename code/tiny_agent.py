import os, openai, pandas as pd, json, time, logging, argparse, warnings, atexit, boto3, requests
from abc import ABC, abstractmethod
# from openai.embeddings_utils import get_embedding, cosine_similarity
from datetime import datetime
# from functions import *
from typing import Any, Dict, Union
warnings.simplefilter('ignore', FutureWarning)

MAX_ATTEMPTS, MAX_TOKEN_LENGTH, PREVIEW_LENGTH = 3, 512, 250

def validate_config(config):
    assert all(key in config for key in ["AgentCode", "LLM"]), "Both AgentCode and LLM sub-agents are required"
    assert "control_flow" in config["AgentCode"], "AgentCode must have a 'control_flow' key"
    assert all(key in config["LLM"] for key in ["prompt_model", "action_model", "api_key", "functions"]), "LLM is missing required keys"
    return True

class Agent:
    """Main Agent class that orchestrates sub-agents."""
    def __init__(self, sub_agents: Dict[str, Any]):
        self.initialize_agent(sub_agents)
        self.initialize_memory_modules()
            
    def initialize_agent(self, sub_agents: Dict[str, Any]):
        self.sub_agents = sub_agents
        self.agent_code = AgentCode(sub_agents["AgentCode"])
        self.llm = LLM(sub_agents["LLM"])
        self.working_memory = ""
        self.max_token_length = self.llm.config.get("max_token_length", MAX_TOKEN_LENGTH)
        self.token_counter = 0
        self.status = "BEGIN"

    def initialize_memory_modules(self):
        self.memory_modules = self.sub_agents.get("MemoryModules", [])
        for memory_module in self.memory_modules:
            get_memory_module(memory_module)
    
    @staticmethod
    def create_output_folder(agent_name: str, timestamp: str) -> str:
        folder_name = f"{agent_name}_{timestamp}"
        folder_path = os.path.join(os.getcwd(), folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        return folder_path

    def _add_to_working_memory(self, input_data: str) -> None:
        """Adds the input_data to working memory, considering token constraints."""
        self.working_memory += f" {input_data}"
        self.token_counter += len(input_data.split())
        
        self._truncate_memory()
        self._ensure_objective()

    def _truncate_memory(self):
        if self.token_counter > self.max_token_length:
            tokens = self.working_memory.split()[-self.max_token_length:]
            self.working_memory, self.token_counter = ' '.join(tokens), self.max_token_length

    def _ensure_objective(self):
        if self.agent_code.objective not in self.working_memory:
            objective = f"Objective: {self.agent_code.objective}"
            self.working_memory = f"{objective} {self.working_memory}"
            self.token_counter += len(objective.split())

    def execute(self, phase: str, input_data: Any) -> Any:
        """Executes a particular phase using sub-agents."""
        start_time = time.time()
        template = self.agent_code.template(phase, input_data)
        self._add_to_working_memory(template)
        
        output = self.llm.prompt(self.working_memory)
        elapsed_time = time.time() - start_time
        
        return output

    def run(self):
        results = {}
        stage, ct = "BEGIN", 0
        while True:
            ct += 1
            
            if stage == "BEGIN":
                stage = self._begin_stage()  
            elif stage == "ACTION":
                stage_results = self._action_stage()
                stage = self.agent_code.control_flow[stage]
            elif stage == "END":
                return results
            else:
                stage_results = self._execute_stage(stage)
                results[stage] = stage_results[0]
                stage = stage_results[1]

    def _begin_stage(self):
        return self.agent_code.control_flow["BEGIN"]

    def _execute_stage(self, stage):
        output_data = self.execute(stage, self.working_memory)
        if "XXTERMINATEXX" in output_data:
            self.status = "END"
        self.working_memory = output_data
        return (output_data, self.agent_code.control_flow[stage])

    def _action_stage(self):
        action_results = self.llm.act(self.working_memory)
        self._add_to_working_memory(f"{action_results['action']} {action_results['output']}")

class AgentCode:
    def __init__(self, config: Dict[str, Any]):
        if "control_flow" not in config:
            raise ValueError("Missing required key 'control_flow' in config")
        
        self.config = config
        self.objective = config["objective"] if "objective" in config else input("What is my purpose? ")
        self.control_flow = config["control_flow"]
        self.name = config.get("name", "TinyAgent")
    
    def template(self, phase: str, input_data: Any) -> Any:
        if phase not in self.config:
            raise ValueError(f"Undefined phase: {phase}")
        return self.config[phase].format(input_data)

class LLM:
    """Large Language Model for generating text."""
    def __init__(self, config: Dict[str, Any]):
        """Initializes the LLM with the necessary configurations."""
        self.config = config
        self.prompt_service, self.prompt_model = config["prompt_model"].split("/")
        self.action_service, self.action_model = config["action_model"].split("/")
        openai.api_key = os.getenv("OPENAI_API_KEY", config["api_key"])
        self.functions = config["functions"]
        self.max_action_attempts = config.get("max_action_attempts", MAX_ATTEMPTS)
        self.system_message = config.get("system_message", "You are a helpful assistant.")

    def prompt(self, input_data: Any) -> str:
        """Generates text based on the input data."""
        if self.prompt_model in ['gpt-4', 'gpt-3.5-turbo']:
                client = openai.OpenAI(api_key="ADD_YOUR_API_KEY_HERE")
                response = client.chat.completions.create(
                model=self.prompt_model,
                messages = [{"role": "system", "content": self.system_message},{"role": "user", "content": input_data}]             
                )
                return response.choices[0].message.content
        
        elif self.prompt_model in ["meta.llama2-13b-chat-v1", "anthropic.claude-v2"]:
            # use Amazon Bedrock API
            bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')

            if self.prompt_model == "meta.llama2-13b-chat-v1":
                prompt = f"<s>[INST] <<SYS>>\n{self.system_message}\n<<SYS>>\n\n{input_data} [/INST]"
                body = json.dumps({
                "prompt": prompt,
                "max_gen_len": 256,
                "temperature": 0.5,
                "top_p": 0.9,
                })
            elif self.prompt_model == "anthropic.claude-v2":
                prompt = f"\n\nHuman: You are an AI chatbot assistant that helps customers answer prompting questions. When I write BEGIN DIALOGUE, all text that comes afterward will be that of a user interacting with you, asking for prompting help.\nHe is the persona you are to adopt during the following conversation:\n<persona>\n{self.system_message}\n</persona>\nBEGIN DIALOGUE\n{input_data}\nAssistant:"
                body = json.dumps({
                    "prompt": prompt,
                    "max_tokens_to_sample": 256,
                    "temperature": 0.5,
                    "top_p": 0.9,
                })

            modelId = self.prompt_model
            accept = 'application/json'
            contentType = 'application/json'

            response = bedrock.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)
            response_body = json.loads(response.get('body').read())
            if self.prompt_model == "meta.llama2-13b-chat-v1":
                return response_body.get('generation')
            elif self.prompt_model == "anthropic.claude-v2":
                return response_body.get('completion')
                
        elif self.prompt_model == "mistral":
            url = "https://mistral.llm-among-us.org/v1/chat/completions"
            messages = [{"role": "system", "content": self.system_message},{"role": "user", "content": input_data}]
            body = json.dumps({
                "messages": messages,
            })
            response = requests.post(url, data=body, headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
            response = response.json()
            return response["choices"][0]["message"]["content"]     




    def act(self, input_data: Any) -> Union[None, Dict[str, Any]]:
        """Attempts to perform an action based on input data."""
        if self.action_model not in ["gpt-3.5-turbo-0613", "gpt-4-0613"]:
            raise NotImplementedError("Only certain models are supported.")

        for attempt in range(self.max_action_attempts):
            response = self._get_function_response(input_data)
            if response is not None:
                return response

            print(f"Attempt {attempt + 1} at calling function failed. Trying again.")

        print("Max attempts reached. Unable to call a function.")
        return None
    
    def _get_function_response(self, input_data: Any) -> Union[None, Dict[str, Any]]:
        """Retrieves the function call from the action model."""
        response = openai.ChatCompletion.create(
            model=self.action_model,
            messages=[{"role": "user", "content": f"You must call a function.\n{input_data}\nRemember, you must call a function."}],
            functions=list(self.functions[0].values()),
            function_call="auto"
        )
        
        response_message = response["choices"][0]["message"]
        
        if not response_message.get("function_call"):
            return None

        available_functions = {k: globals()[k] for d in self.functions for k in d.keys()}
        function_name = response_message["function_call"]["name"]

        function_to_call = available_functions.get(function_name)
        if function_to_call is None:
            print(f"Function {function_name} not found.")
            return None

        function_args = json.loads(response_message["function_call"]["arguments"])
        function_response = function_to_call(**function_args)

        if function_response is None:
            return None

        return {"action": function_name, "output": function_response}

class MemoryModule(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def embed(self, text: str) -> Any:
        pass

    @abstractmethod
    def learn(self, text: str):
        pass

    @abstractmethod
    def retrieve(self, text: str) -> str:
        pass

def get_memory_module(config: Dict[str, Any]) -> MemoryModule:
    pass
