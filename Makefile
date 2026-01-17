# Makefile for pyralph
# Global installation via uv tool

.PHONY: install update uninstall help

## install: Install ralph globally using uv tool (accessible from any directory)
install:
	@echo "Installing ralph globally via uv tool..."
	uv tool install . --force
	@echo ""
	@echo "Done! The 'ralph' command is now available globally."
	@echo "Make sure ~/.local/bin is in your PATH."
	@echo ""
	@echo "Test with: ralph --help"

## update: Update ralph to the latest version from this repo
update:
	@echo "Updating ralph to latest version..."
	uv tool install . --force
	@echo ""
	@echo "Done! ralph has been updated."

## uninstall: Remove ralph global installation
uninstall:
	@echo "Uninstalling ralph..."
	uv tool uninstall pyralph
	@echo "Done!"

## help: Show this help message
help:
	@echo "Available targets:"
	@echo ""
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /'
