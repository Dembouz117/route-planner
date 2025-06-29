import uuid
from typing import Dict, Any, Literal
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
        """Create the Information Agent workflow with proper ReAct pattern"""
        workflow = StateGraph(InformationAgentState)
        
        # Add nodes
        workflow.add_node("react_agent", self._react_agent_node)
        workflow.add_node("check_completion", self._check_completion_node)
        workflow.add_node("finalize_analysis", self._finalize_analysis_node)
        
        # Add edges with loops back to agent for continued reasoning
        workflow.add_edge(START, "react_agent")
        workflow.add_conditional_edges(
            "react_agent",
            self._should_continue_analysis,
            {
                "continue": "react_agent",  # Loop back for more tool usage
                "check": "check_completion"
            }
        )
        workflow.add_conditional_edges(
            "check_completion",
            self._is_analysis_complete,
            {
                "continue": "react_agent",  # Loop back if more work needed
                "finalize": "finalize_analysis"
            }
        )
        workflow.add_edge("finalize_analysis", END)
        
        # Compile with memory
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    def _react_agent_node(self, state: InformationAgentState) -> InformationAgentState:
        """Node where Claude uses ReAct pattern to decide and use tools"""
        print(f"🤖 Information Agent: Analyzing supply chain for region '{state['region']}'")
        
        # Determine what prompt to give Claude based on current state
        if not state.get("messages") or len(state["messages"]) == 0:
            # Initial analysis prompt
            analysis_prompt = f"""
            You are a supply chain intelligence analyst. Your task is to gather comprehensive information about supply chain conditions for the {state['region']} region.

            Query: {state['query']}
            Region: {state['region']}

            You have access to the following tools:
            1. search_domain_knowledge - Search internal knowledge base for supply chain best practices and guidelines
            2. search_supply_chain_disruptions - Search for current disruptions, port closures, conflicts, and news
            3. analyze_supply_chain_risks - Analyze risks based on gathered domain knowledge and disruption data

            Please start by searching for relevant domain knowledge about supply chain operations in {state['region']}, then search for current disruptions that might affect this region, and finally analyze the overall risk situation.

            Use the tools systematically to gather comprehensive intelligence.
            """
        else:
            # Continuation prompt based on what's been done
            analysis_prompt = f"""
            Continue your supply chain analysis for {state['region']}.
            
            Current progress:
            - Domain knowledge items: {len(state.get('domain_knowledge', []))}
            - Disruption data items: {len(state.get('disruption_data', []))}
            - Risk assessment: {'completed' if state.get('risk_assessment') else 'pending'}
            
            If you haven't gathered enough information, continue using the available tools.
            If you have sufficient data, provide a comprehensive analysis summary.
            """
        
        # Create message list for the agent
        if not state.get("messages"):
            messages = [HumanMessage(content=analysis_prompt)]
        else:
            # Add continuation prompt to existing conversation
            messages = state["messages"] + [HumanMessage(content=analysis_prompt)]
        
        # Invoke the ReAct agent - Claude will decide which tools to use
        agent_config = {"configurable": {"thread_id": f"info_agent_{state.get('current_step', uuid.uuid4())}"}}
        result = self.react_agent.invoke(
            {"messages": messages},
            config=agent_config
        )
        
        # Update state with new messages from the agent interaction
        state["messages"] = result["messages"]
        state["current_step"] = "agent_processing"
        
        # Extract any tool results from the conversation to update state
        self._extract_tool_results_from_messages(state)
        
        return state
    
    def _extract_tool_results_from_messages(self, state: InformationAgentState):
        """Extract tool results from agent messages and update state"""
        print(f"🔍 Extracting tool results from {len(state['messages'])} messages")
        
        # Look through all messages for tool calls and their results
        for i, message in enumerate(state["messages"]):
            print(f"🔍 Message {i}: Type={type(message).__name__}")
            
            # Handle tool calls in AIMessage content (Claude's format)
            if hasattr(message, 'content') and isinstance(message.content, list):
                for content_item in message.content:
                    if isinstance(content_item, dict):
                        if content_item.get('type') == 'tool_use':
                            tool_name = content_item.get('name', '')
                            tool_id = content_item.get('id', '')
                            print(f"🔧 Found tool use: {tool_name} with ID: {tool_id}")
                            
                            # Find the result for this tool call
                            tool_result = self._find_tool_result_by_id(state["messages"], tool_id, i)
                            print(f"🔧 Tool result for {tool_name}: {tool_result is not None}")
                            
                            if tool_result:
                                self._update_state_with_tool_result(state, tool_name, tool_result)
            
            # Also handle direct tool calls attribute (LangChain format)
            elif hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.get("name", "")
                    tool_id = tool_call.get("id", "")
                    print(f"🔧 Found tool call: {tool_name} with ID: {tool_id}")
                    
                    # Find the result for this tool call
                    tool_result = self._find_tool_result_by_id(state["messages"], tool_id, i)
                    print(f"🔧 Tool result for {tool_name}: {tool_result is not None}")
                    
                    if tool_result:
                        self._update_state_with_tool_result(state, tool_name, tool_result)
        
        print(f"🔍 Final state - Domain: {len(state.get('domain_knowledge', []))}, Disruptions: {len(state.get('disruption_data', []))}, Risk: {bool(state.get('risk_assessment'))}")
    
    def _find_tool_result_by_id(self, messages, tool_call_id, start_index):
        """Find tool result starting from a specific message index"""
        # Look in messages after the tool call
        for msg in messages[start_index:]:
            # Check for ToolMessage type
            if hasattr(msg, 'tool_call_id') and msg.tool_call_id == tool_call_id:
                content = getattr(msg, 'content', None)
                return self._parse_tool_content(content)
            
            # Check for tool results in Claude's content format
            if hasattr(msg, 'content') and isinstance(msg.content, list):
                for content_item in msg.content:
                    if isinstance(content_item, dict) and content_item.get('type') == 'tool_result':
                        if content_item.get('tool_use_id') == tool_call_id:
                            return self._parse_tool_content(content_item.get('content'))
            
            # Check for tool results in string content format
            elif hasattr(msg, 'content') and isinstance(msg.content, str):
                # Sometimes tool results are embedded in the message content
                if tool_call_id in msg.content:
                    return self._parse_tool_content(msg.content)
        
        return None
    
    def _parse_tool_content(self, content):
        """Parse tool content to extract the actual result"""
        if isinstance(content, str):
            try:
                import json
                return json.loads(content)
            except (json.JSONDecodeError, TypeError):
                return content
        return content
    
    def _update_state_with_tool_result(self, state: InformationAgentState, tool_name: str, tool_result):
        """Update state with a specific tool result"""
        if tool_name == "search_domain_knowledge":
            if not state.get("domain_knowledge"):
                state["domain_knowledge"] = []
            if isinstance(tool_result, list):
                state["domain_knowledge"].extend(tool_result)
                print(f"✅ Added {len(tool_result)} domain knowledge items")
            elif isinstance(tool_result, dict):
                state["domain_knowledge"].append(tool_result)
                print(f"✅ Added 1 domain knowledge item")
                
        elif tool_name == "search_supply_chain_disruptions":
            if not state.get("disruption_data"):
                state["disruption_data"] = []
            if isinstance(tool_result, list):
                state["disruption_data"].extend(tool_result)
                print(f"✅ Added {len(tool_result)} disruption items")
            elif isinstance(tool_result, dict):
                state["disruption_data"].append(tool_result)
                print(f"✅ Added 1 disruption item")
                
        elif tool_name == "analyze_supply_chain_risks":
            if isinstance(tool_result, dict):
                state["risk_assessment"] = tool_result
                print(f"✅ Added risk assessment")
            else:
                print(f"⚠️ Risk assessment result is not a dict: {type(tool_result)}")
    
    def _find_tool_result(self, messages, tool_call_id):
        """Find tool result message corresponding to a tool call"""
        for msg in messages:
            # Check for ToolMessage type (LangChain's tool result message)
            if hasattr(msg, 'tool_call_id') and msg.tool_call_id == tool_call_id:
                content = getattr(msg, 'content', None)
                # Try to parse JSON if it's a string
                if isinstance(content, str):
                    try:
                        import json
                        return json.loads(content)
                    except (json.JSONDecodeError, TypeError):
                        return content
                return content
            
            # Also check if this is a tool response in the content
            if hasattr(msg, 'content') and isinstance(msg.content, list):
                # Claude's response format with tool results
                for content_item in msg.content:
                    if isinstance(content_item, dict) and content_item.get('type') == 'tool_result':
                        if content_item.get('tool_use_id') == tool_call_id:
                            return content_item.get('content')
        
        return None
    
    def _should_continue_analysis(self, state: InformationAgentState) -> Literal["continue", "check"]:
        """Determine if Claude should continue using tools or move to completion check"""
        # Check the last message from Claude
        if state.get("messages"):
            last_message = state["messages"][-1]
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                # Claude is still making tool calls, let it continue
                return "continue"
            
            # Check if Claude's last response indicates it's done with tool usage
            last_content = getattr(last_message, 'content', '').lower()
            if any(phrase in last_content for phrase in [
                "analysis complete", "comprehensive analysis", "summary", 
                "conclusion", "final assessment", "ready for route planning"
            ]):
                return "check"
        
        # Default to continuing if unclear
        return "continue"
    
    def _check_completion_node(self, state: InformationAgentState) -> InformationAgentState:
        """Check if analysis is complete based on gathered data"""
        print("📊 Information Agent: Checking analysis completeness")
        
        # Check what data we have
        domain_count = len(state.get("domain_knowledge", []))
        disruption_count = len(state.get("disruption_data", []))
        has_risk_assessment = bool(state.get("risk_assessment"))
        
        print(f"🔍 Information Agent: Domain count: {domain_count}, Disruption count: {disruption_count}, Risk assessment: {has_risk_assessment}")
        
        # Update current step
        state["current_step"] = f"checking_completion_d{domain_count}_dis{disruption_count}_risk{has_risk_assessment}"
        
        return state
    
    def _is_analysis_complete(self, state: InformationAgentState) -> Literal["continue", "finalize"]:
        """Determine if we have sufficient data or need more analysis"""
        domain_count = len(state.get("domain_knowledge", []))
        disruption_count = len(state.get("disruption_data", []))
        has_risk_assessment = bool(state.get("risk_assessment"))
        
        # Consider analysis complete if we have reasonable data in each category
        if domain_count >= 1 and disruption_count >= 1 and has_risk_assessment:
            return "finalize"
        
        # Need more data
        return "continue"
    
    def _finalize_analysis_node(self, state: InformationAgentState) -> InformationAgentState:
        """Finalize the analysis with summary"""
        print("✅ Information Agent: Finalizing analysis")
        
        state["analysis_complete"] = True
        state["current_step"] = "analysis_complete"
        
        # Add final summary message
        summary = f"""Analysis complete for {state['region']}:
        - Found {len(state.get('domain_knowledge', []))} domain knowledge entries
        - Identified {len(state.get('disruption_data', []))} potential disruptions
        - Risk level assessed as: {state.get('risk_assessment', {}).get('overall_risk', 'unknown')}
        - Ready for route planning optimization"""
        
        state["messages"].append(AIMessage(content=summary))
        
        return state
    
    async def analyze_supply_chain(self, task_id: str, query: str, region: str, task_storage) -> Dict[str, Any]:
        """Run the complete information analysis workflow"""
        
        # Create LangSmith run for tracking
        run = None
        if langsmith_config.enabled:
            run = langsmith_config.create_run(
                name=f"Information Agent Analysis - {region}",
                run_type="chain",
                inputs={"task_id": task_id, "query": query, "region": region}
            )
        
        try:
            config = {"configurable": {"thread_id": f"info_{task_id}"}, "recursion_limit": 20}
            
            # Add callbacks to config if LangSmith is enabled
            if langsmith_config.enabled and run:
                config["callbacks"] = langsmith_config.get_callbacks()
                config["run_id"] = run.id
            
            initial_state = {
                "messages": [],
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
                # Update task status
                for node_name, node_state in state.items():
                    if node_name != "__end__":
                        current_step = node_state.get('current_step', 'processing')
                        progress = 30 if "checking" in current_step else 50 if "processing" in current_step else 80
                        task_storage.update_task(task_id, {
                            "current_step": f"info_agent_{current_step}",
                            "progress": progress
                        })
            
            # Extract final analysis from the completed workflow
            final_state = final_result.get("finalize_analysis", final_result)
            if not final_state:
                # Fallback to any available state
                final_state = list(final_result.values())[-1] if final_result else {}
            
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
        test_config = {"configurable": {"thread_id": f"test_info_{uuid.uuid4()}"}, "recursion_limit": 20}
        initial_state = {
            "messages": [],
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
        
        # Get the final state
        final_state = final_result.get("finalize_analysis", final_result)
        if not final_state:
            final_state = list(final_result.values())[-1] if final_result else {}
        
        return {
            "final_state": final_state,
            "agent_messages": [msg.content for msg in final_state.get("messages", [])],
            "llm_reasoning": "Claude LLM used for intelligent tool selection and analysis"
        }
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get workflow information for debugging"""
        try:
            graph_dict = self.workflow.get_graph().to_json()
            return {
                "workflow_type": "Information Agent with Claude LLM ReAct",
                "llm_model": "claude-3-5-sonnet-20241022",
                "agent_type": "ReAct Agent with Looping",
                "tools_available": [tool.name for tool in self.tools],
                "graph_structure": graph_dict,
                "nodes": ["react_agent", "check_completion", "finalize_analysis"],
                "description": "LLM decides which tools to use and when, with loops back for continued reasoning"
            }
        except Exception as e:
            return {"error": str(e)}