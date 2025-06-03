#!/usr/bin/env bash
DATE=$(date +%F)
pg_dump -U mcp -h pg -d mcp | gzip > /backups/mcp_$DATE.sql.gz
