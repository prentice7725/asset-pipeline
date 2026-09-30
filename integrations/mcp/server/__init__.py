"""Local stdio MCP server exposing only the six M0 tools."""
import argparse
import asyncio
import os
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from ..tools.adapter import Adapter
from jsonschema import Draft202012Validator

class StrictMCP(FastMCP):
    async def list_tools(self):
        tools = await super().list_tools()
        for tool in tools:
            tool.inputSchema['additionalProperties'] = False
        return tools

    async def call_tool(self, name, arguments):
        tools = {tool.name: tool for tool in await self.list_tools()}
        if name not in tools:
            raise ValueError('Unknown tool')
        Draft202012Validator(tools[name].inputSchema).validate(arguments)
        return await super().call_tool(name, arguments)

def create_server(config):
    adapter = Adapter(config)
    server = StrictMCP('Asset Pipeline', instructions='Build a source-grounded Asset Brief, route, then generate. Never bypass review gates.', log_level='WARNING')
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)

    @server.tool(annotations=read)
    async def asset_capabilities() -> dict:
        """Return registry-backed capabilities and actual local provider readiness."""
        return await asyncio.to_thread(adapter.capabilities)

    @server.tool(annotations=read)
    def asset_build_brief(request_text: str, requested_output_type: str | None = None, asset_id: str = 'asset', source_document_paths: list[str] | None = None, reference_image: str | None = None, action: str | None = None, prepared_brief: dict | None = None, workflow_id: str | None = None, project_id: str | None = None, duration_seconds: float | None = None) -> dict:
        """Validate a brief; project canon must come from explicit source extraction, never inference."""
        return adapter.build_brief(request_text=request_text, output_class=requested_output_type, asset_id=asset_id, source_documents=source_document_paths or [], reference_image=reference_image, action=action, prepared_brief=prepared_brief, workflow_id=workflow_id, project_id=project_id, duration_seconds=duration_seconds)

    @server.tool(annotations=read)
    def asset_route(brief: dict) -> dict:
        """Route without generation and report missing production requirements."""
        return adapter.route(brief)

    @server.tool(annotations=write)
    def asset_generate(brief: dict | None = None, brief_file: str | None = None, seed: int | None = None) -> dict:
        """Launch the existing assetpipe CLI; return run ID immediately and inspect its manifest later."""
        return adapter.generate(brief=brief, brief_file=brief_file, seed=seed)

    @server.tool(annotations=write)
    def asset_continue_animation(asset_reference: str, action: str, output_class: str = 'PIXEL_ANIMATION', animation_constraints: dict | None = None) -> dict:
        """Continue an approved master using the existing primary path; unsupported/missing inputs block."""
        return adapter.continue_animation(asset_reference, action, output_class, animation_constraints or {})

    @server.tool(annotations=read)
    def asset_inspect_run(run_id: str) -> dict:
        """Read manifest, route, QA, produced-file references, and required reviews."""
        return adapter.inspect(run_id)
    return server

def main():
    parser = argparse.ArgumentParser(description='Asset Pipeline M0 local stdio MCP adapter')
    parser.add_argument('--config', default=os.environ.get('ASSETPIPE_MCP_CONFIG'), help='Host-controlled adapter config; defaults to ASSETPIPE_MCP_CONFIG')
    args = parser.parse_args()
    if not args.config:
        parser.error('--config or ASSETPIPE_MCP_CONFIG is required')
    create_server(args.config).run(transport='stdio')
