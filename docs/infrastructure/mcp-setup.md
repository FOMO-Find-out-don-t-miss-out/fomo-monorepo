# MCP Bridge for Real-Time Infrastructure Awareness

## Overview
To ensure that AI agents have real-time access to the live database schema, we use the Model Context Protocol (MCP). This bridge allows agents to inspect PostgreSQL tables, PostGIS columns, and indexes directly.

## Setup
The configuration is located in `infra/mcp-config.json`. AI agents can use this configuration to connect to the local PostgreSQL instance.

## Benefits
- **Prevention of Migration Drift**: Agents can verify the actual schema before proposing SQLModel changes.
- **Zero-Hallucination Queries**: Agents can inspect column types and constraints to write accurate queries.
- **Spatial Awareness**: Direct inspection of PostGIS geometry columns and spatial indexes.

## Usage for AI Agents
Before proposing any database migration or SQLModel change, the Agent **MUST** use the MCP Bridge to inspect the current state of the PostgreSQL schema. Proposing changes based on stale context is strictly forbidden.
