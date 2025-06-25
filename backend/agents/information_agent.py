import uuid
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage
from models.schemas import InformationAgentState
from tools.information_tools import KnowledgeSearchTool, DisruptionSearchTool, RiskAnalysisTool

class InformationAgent:
    def __init__(self, pinecone_client, tavily_client):
        self.pinecone_client = pinecone_client
        self.tavily_client = tavily_client
        
        # Initialize tools
        self.knowledge_tool = KnowledgeSearchTool(pinecone_client)
        self.disruption_tool = DisruptionSearchTool(tavily_client)
        self.risk_tool = RiskAnalysisTool()
        
        # Create workflow
        self.workflow = self._create_workflow()
    
    def _create_workflow(self):
        """Create the Information Agent LangGraph workflow"""
        workflow = StateGraph(InformationAgentState)
        
        # Add nodes
        workflow.add_node("knowledge_search", self._knowledge_search_node)
        workflow.add_node("disruption_search", self._disruption_search_node)
        workflow.add_node("risk_synthesis", self._risk_synthesis_node)
        
        # Add edges
        workflow.add_edge(START, "knowledge_search")
        workflow.add_edge("knowledge_search", "disruption_search")
        workflow.add_edge("disruption_search", "risk_synthesis")
        workflow.add_edge("risk_synthesis", END)
        
        # Compile with memory
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    def _knowledge_search_node(self, state: InformationAgentState) -> InformationAgentState:
        """Node: Search Dell knowledge base"""
        print(f"🔍 Information Agent: Searching domain knowledge for '{state['query']}'")
        
        domain_results = self.knowledge_tool.search(state["query"], state.get("region"))
        
        state["domain_knowledge"] = domain_results
        state["current_step"] = "knowledge_search_complete"
        state["messages"].append(
            AIMessage(content=f"Found {len(domain_results)} relevant domain knowledge entries")
        )
        
        return state
    
    def _disruption_search_node(self, state: InformationAgentState) -> InformationAgentState:
        """Node: Search for supply chain disruptions"""
        print(f"🌐 Information Agent: Searching for disruptions in region: {state.get('region', 'global')}")
        
        disruption_results = self.disruption_tool.search(state["query"], state.get("region"))
        
        state["disruption_data"] = disruption_results
        state["current_step"] = "disruption_search_complete"
        state["messages"].append(
            AIMessage(content=f"Found {len(disruption_results)} potential supply chain disruptions")
        )
        
        return state
    
    def _risk_synthesis_node(self, state: InformationAgentState) -> InformationAgentState:
        """Node: Synthesize risk assessment from all gathered intelligence"""
        print("⚠️ Information Agent: Synthesizing risk assessment")
        
        risk_assessment = self.risk_tool.analyze(
            state["domain_knowledge"], 
            state["disruption_data"]
        )
        
        state["risk_assessment"] = risk_assessment
        state["analysis_complete"] = True
        state["current_step"] = "analysis_complete"
        state["messages"].append(
            AIMessage(content=f"Risk analysis complete. Overall risk level: {risk_assessment['overall_risk']}")
        )
        
        return state
    
    async def analyze_supply_chain(self, task_id: str, query: str, region: str, task_storage) -> Dict[str, Any]:
        """Run the complete information analysis workflow"""
        config = {"configurable": {"thread_id": f"info_{task_id}"}}
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
                    task_storage.update_task(task_id, {
                        "current_step": f"info_agent_{node_state.get('current_step', 'processing')}"
                    })
        
        # Extract final analysis
        final_state = final_result.get("risk_synthesis", final_result)
        return {
            "domain_knowledge": final_state.get("domain_knowledge", []),
            "disruption_data": final_state.get("disruption_data", []),
            "risk_assessment": final_state.get("risk_assessment", {})
        }
    
    async def test_workflow(self, query: str, region: str) -> Dict[str, Any]:
        """Test the workflow independently"""
        test_config = {"configurable": {"thread_id": f"test_info_{uuid.uuid4()}"}}
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
            "final_state": final_result.get("risk_synthesis", final_result),
            "messages": [msg.content for msg in final_result.get("risk_synthesis", {}).get("messages", [])]
        }
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get workflow information for debugging"""
        try:
            graph_dict = self.workflow.get_graph().to_json()
            return {
                "workflow_type": "Information Agent",
                "graph_structure": graph_dict,
                "nodes": ["knowledge_search", "disruption_search", "risk_synthesis"],
                "description": "Collects domain knowledge and disruption intelligence"
            }
        except Exception as e:
            return {"error": str(e)}
