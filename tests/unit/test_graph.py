import pytest

from uaclient.graph_ui import GraphWidget


@pytest.mark.asyncio
async def test_add_to_graph(qtbot, server):
    namepace = await server.register_namespace("custom_namespace")

    objects = server.nodes.objects
    string_variable = await objects.add_variable(namepace, "string_variable", "Value")
    float_variable = await objects.add_variable(namepace, "float_variable", 1.0)

    client.graph_ui._add_node_to_channel(string_variable)
    client.graph_ui._add_node_to_channel(float_variable)

    # string is not a graphable value and therefore does not get added to the graph
    assert len(client.graph_ui._node_list) == 1
    assert client.graph_ui._node_list[0] == float_variable


def test_remove_from_graph(client, server):
    namepace = server.register_namespace("custom_namespace")
    objects = server.nodes.objects
    float_variable = objects.add_variable(namepace, "float_variable", 1.0)
    client.graph_ui._add_node_to_channel(float_variable)

    client.graph_ui._remove_node_from_channel(float_variable)

    assert len(client.graph_ui._node_list) == 0


def test_restart_timer(client, server):
    client.ui.spinBoxNumberOfPoints.setValue(90)
    client.ui.spinBoxIntervall.setValue(5)
    client.graph_ui.restartTimer()

    assert client.graph_ui.timer.interval() == 5000
    assert client.graph_ui.N == 90
    assert client.graph_ui.timer.isActive()
