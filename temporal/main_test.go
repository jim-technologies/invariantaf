package main

import (
	"testing"

	invariant "github.com/jim-technologies/invariantprotocol/go"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func testServer(t *testing.T) *invariant.Server {
	t.Helper()
	srv, err := invariant.ServerFromBytes(descriptorBytes)
	require.NoError(t, err)
	return srv
}

func TestDescriptorLoads(t *testing.T) {
	srv := testServer(t)
	assert.NotNil(t, srv)
}

func TestToolCount(t *testing.T) {
	srv := testServer(t)
	// Connect without a real server to count registered tools.
	// We use ConnectHTTP with a dummy base URL just to register tools.
	err := srv.ConnectHTTP("http://localhost:7233")
	require.NoError(t, err)
	tools := srv.Tools()
	assert.Greater(t, len(tools), 100, "expected 100+ tools from Temporal API")
	t.Logf("registered %d tools", len(tools))
}

func TestWorkflowServiceToolsPresent(t *testing.T) {
	srv := testServer(t)
	err := srv.ConnectHTTP("http://localhost:7233")
	require.NoError(t, err)
	tools := srv.Tools()

	expected := []string{
		"WorkflowService.StartWorkflowExecution",
		"WorkflowService.DescribeWorkflowExecution",
		"WorkflowService.ListWorkflowExecutions",
		"WorkflowService.GetWorkflowExecutionHistory",
		"WorkflowService.TerminateWorkflowExecution",
		"WorkflowService.SignalWorkflowExecution",
		"WorkflowService.RequestCancelWorkflowExecution",
	}
	for _, name := range expected {
		assert.Contains(t, tools, name, "missing tool: %s", name)
	}
}

func TestOperatorServiceToolsPresent(t *testing.T) {
	srv := testServer(t)
	err := srv.ConnectHTTP("http://localhost:7233")
	require.NoError(t, err)
	tools := srv.Tools()

	expected := []string{
		"OperatorService.AddSearchAttributes",
		"OperatorService.ListSearchAttributes",
		"OperatorService.DeleteNamespace",
	}
	for _, name := range expected {
		assert.Contains(t, tools, name, "missing tool: %s", name)
	}
}

func TestIncludeFilter(t *testing.T) {
	srv := testServer(t)
	srv.Include("temporal.api.workflowservice.v1.WorkflowService.*")
	err := srv.ConnectHTTP("http://localhost:7233")
	require.NoError(t, err)
	tools := srv.Tools()
	// Should only have WorkflowService tools, no OperatorService
	for name := range tools {
		assert.NotContains(t, name, "OperatorService", "should not include OperatorService tools")
	}
	assert.Greater(t, len(tools), 50, "expected many WorkflowService tools")
}

func TestExcludeFilter(t *testing.T) {
	srv := testServer(t)
	srv.Exclude("*Poll*", "*Respond*")
	err := srv.ConnectHTTP("http://localhost:7233")
	require.NoError(t, err)
	tools := srv.Tools()
	for name := range tools {
		assert.NotContains(t, name, "Poll", "Poll methods should be excluded")
		assert.NotContains(t, name, "Respond", "Respond methods should be excluded")
	}
}
