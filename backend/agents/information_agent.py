import uuid
import json
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_anthropic import ChatAnthropic
from models.schemas import InformationAgentState
from tools.information_tools import (
    search_domain_knowledge,
    search_supply_chain_disruptions,
    analyze_supply_chain_risks
)
from config.langsmith_config import langsmith_config


class InformationAgent:
    def __init__(self, anthropic_api_key: str):
        # Initialize Claude LLM
        self.llm = ChatAnthropic(
            api_key=anthropic_api_key,
            model="claude-3-5-sonnet-20241022",
            temperature=0.1,
            max_tokens=4000
        )
        
        # Define tools for the agent
        self.tools = [
            search_domain_knowledge,
            search_supply_chain_disruptions,
            analyze_supply_chain_risks
        ]
        
        # Create ReAct agent with Claude and tools
        self.react_agent = create_react_agent(self.llm, self.tools)
        
        # Create the main workflow
        self.workflow = self._create_workflow()
    
    def _create_workflow(self):
        """Create the Information Agent workflow using ReAct pattern"""
        workflow = StateGraph(InformationAgentState)
        
        # Add nodes
        workflow.add_node("information_agent", self._agent_node)
        workflow.add_node("process_results", self._process_results_node)
        
        # Add edges
        workflow.add_edge(START, "information_agent")
        workflow.add_edge("information_agent", "process_results")
        workflow.add_edge("process_results", END)
        
        # Compile with memory only (no callbacks in compile)
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    def _agent_node(self, state: InformationAgentState) -> InformationAgentState:
        """Node where the ReAct agent processes the supply chain analysis request"""
        print(f"🤖 Information Agent: Analyzing supply chain for region '{state['region']}'")
        
        # Create a comprehensive prompt for the agent
        analysis_prompt = f"""
        You are a supply chain intelligence analyst. Analyze the supply chain situation for the {state['region']} region.
        
        Your task:
        1. Search for relevant domain knowledge about supply chain best practices for {state['region']}
        2. Search for current supply chain disruptions that might affect {state['region']}
        3. Analyze the risks based on the gathered information
        
        Query context: {state['query']}
        Region focus: {state['region']}
        
        Please provide a comprehensive analysis using the available tools.
        """
        
        # Invoke the ReAct agent
        agent_config = {"configurable": {"thread_id": f"info_agent_{uuid.uuid4()}"}}
        result = self.react_agent.invoke(
            {"messages": [HumanMessage(content=analysis_prompt)]},
            config=agent_config
        )
        
        # Extract the agent's response
        if result and "messages" in result:
            agent_response = result["messages"][-1].content if result["messages"] else "No response generated"
        else:
            agent_response = "Agent processing completed"
        
        # Update state with agent's work
        state["messages"].extend([
            HumanMessage(content=analysis_prompt),
            AIMessage(content=agent_response)
        ])
        state["current_step"] = "agent_analysis_complete"
        
        return state
    
    def _process_results_node(self, state: InformationAgentState) -> InformationAgentState:
        """Node to process and structure the agent's findings"""
        print("📊 Information Agent: Processing and structuring results")
        
        # Initialize result containers
        domain_knowledge = []
        disruption_data = []
        risk_assessment = {}
        
        # Look for tool calls in the agent's message history
        for message in state["messages"]:
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.get("name", "")
                    if tool_name == "search_domain_knowledge":
                        # This would be the actual result from the tool
                        domain_knowledge = self._extract_tool_result(tool_call, "domain")
                    elif tool_name == "search_supply_chain_disruptions":
                        disruption_data = self._extract_tool_result(tool_call, "disruption")
                    elif tool_name == "analyze_supply_chain_risks":
                        risk_assessment = self._extract_tool_result(tool_call, "risk")
        
        # If no tool results found in messages, run the tools directly to ensure we have data
        if not domain_knowledge:
            domain_knowledge = search_domain_knowledge.invoke({
                "query": state["query"], 
                "region": state["region"]
            })
        
        if not disruption_data:
            disruption_data = search_supply_chain_disruptions.invoke({
                "query": f"supply chain disruption {state['region']}", 
                "region": state["region"]
            })
        
        if not risk_assessment:
            risk_assessment = analyze_supply_chain_risks.invoke({
                "domain_knowledge": json.dumps(domain_knowledge),
                "disruption_data": json.dumps(disruption_data)
            })
        
        # Update state with structured results
        state["domain_knowledge"] = domain_knowledge
        state["disruption_data"] = disruption_data
        state["risk_assessment"] = risk_assessment
        state["analysis_complete"] = True
        state["current_step"] = "analysis_complete"
        
        # Add summary message
        summary = f"""Analysis complete for {state['region']}:
        - Found {len(domain_knowledge)} domain knowledge entries
        - Identified {len(disruption_data)} potential disruptions
        - Risk level assessed as: {risk_assessment.get('overall_risk', 'unknown')}"""
        
        state["messages"].append(AIMessage(content=summary))
        
        return state
    
    def _extract_tool_result(self, tool_call: Dict, result_type: str) -> Any:
        """Extract results from tool calls (simplified for mock implementation)"""
        # In a real implementation, this would extract actual tool results
        # For now, return empty structures that will trigger direct tool calls
        return [] if result_type in ["domain", "disruption"] else {}
    
    async def analyze_supply_chain(self, task_id: str, query: str, region: str, task_storage) -> Dict[str, Any]:
        """Run the complete information analysis workflow with LLM reasoning"""
        
        # Create LangSmith run for tracking
        run = None
        if langsmith_config.enabled:
            run = langsmith_config.create_run(
                name=f"Information Agent Analysis - {region}",
                run_type="chain",
                inputs={"task_id": task_id, "query": query, "region": region}
            )
        
        try:
            config = {"configurable": {"thread_id": f"info_{task_id}"}, "recursion_limit": 10}
            # Add callbacks to config, not compile
            if langsmith_config.enabled and run:
                config["callbacks"] = langsmith_config.get_callbacks()
                config["run_id"] = run.id
            
            initial_state = {
                "messages": [HumanMessage(content=f"Analyze supply chain for {region}")],
                "query": query,
                "region": region,
                "domain_knowledge": [],
                "disruption_data": [],
                "risk_assessment": {},
                "analysis_complete": False,
                "current_step": "starting"
            }
            
            final_result = None
            async for state in self.workflow.astream(initial_state, config=config):
                final_result = state
                # Update task status with current step
                for node_name, node_state in state.items():
                    if node_name != "__end__":
                        current_step = node_state.get('current_step', 'processing')
                        task_storage.update_task(task_id, {
                            "current_step": f"info_agent_{current_step}",
                            "progress": 50 if current_step == "agent_analysis_complete" else 80
                        })
            
            # Extract final analysis
            final_state = final_result.get("process_results", final_result)
            result = {
                "domain_knowledge": final_state.get("domain_knowledge", []),
                "disruption_data": final_state.get("disruption_data", []),
                "risk_assessment": final_state.get("risk_assessment", {}),
                "agent_reasoning": [msg.content for msg in final_state.get("messages", []) if isinstance(msg, AIMessage)]
            }
            
            # Update LangSmith run with outputs
            if run and langsmith_config.client:
                langsmith_config.client.update_run(
                    run.id,
                    outputs=result,
                    end_time=None
                )
            
            return result
            
        except Exception as e:
            if run and langsmith_config.client:
                langsmith_config.client.update_run(
                    run.id,
                    status="failed",
                    error=str(e)
                )
            raise e

    async def test_workflow(self, query: str, region: str) -> Dict[str, Any]:
        """Test the workflow independently"""
        test_config = {"configurable": {"thread_id": f"test_info_{uuid.uuid4()}"}, "recursion_limit": 10}
        initial_state = {
            "messages": [HumanMessage(content=f"Test analysis for {region}")],
            "query": query,
            "region": region,
            "domain_knowledge": [],
            "disruption_data": [],
            "risk_assessment": {},
            "analysis_complete": False,
            "current_step": "starting"
        }
        
        final_result = {}
        async for state in self.workflow.astream(initial_state, config=test_config):
            final_result = state
        
        return {
            "final_state": final_result.get("process_results", final_result),
            "agent_messages": [msg.content for msg in final_result.get("process_results", {}).get("messages", [])],
            "llm_reasoning": "Claude LLM used for intelligent analysis and tool selection"
        }
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get workflow information for debugging"""
        try:
            graph_dict = self.workflow.get_graph().to_json()
            return {
                "workflow_type": "Information Agent with Claude LLM",
                "llm_model": "claude-3-sonnet-20240229",
                "agent_type": "ReAct Agent",
                "tools_available": [tool.name for tool in self.tools],
                "graph_structure": graph_dict,
                "nodes": ["information_agent", "process_results"],
                "description": "LLM-powered agent that uses tools to collect domain knowledge and disruption intelligence"
            }
        except Exception as e:
            return {"error": str(e)}