import aiosqlite
from aiohttp import web
from chia.data_layer.data_store import DataStore
from chia.util.db_wrapper import DBWrapper
from chia.types.blockchain_format.tree_hash import bytes32
from tests.core.data_layer.util import generate_big_datastore


class DataLayerServer:
    async def handle_tree_root(self, request: web.Request) -> web.Response:
        tree_id = request.rel_url.query["tree_id"]
        tree_id_bytes = bytes32.from_hexstr(tree_id)
        tree_root = await self.data_store.get_tree_root(tree_id_bytes)
        result = {
            "tree_id": tree_id,
            "generation": tree_root.generation,
            "node_hash": str(tree_root.node_hash),
            "status": tree_root.status.value,
        }
        return web.json_response(result)

    async def handle_tree_nodes(self, request: web.Request) -> web.Response:
        node_hash = request.rel_url.query["node_hash"]
        tree_id = request.rel_url.query["tree_id"]
        root_hash = request.rel_url.query["root_hash"]
        node_hash_bytes = bytes32.from_hexstr(node_hash)
        tree_id_bytes = bytes32.from_hexstr(tree_id)
        root_hash_bytes = bytes32.from_hexstr(root_hash)
        root_changed, answer = await self.data_store.get_left_to_right_ordering(
            node_hash_bytes, tree_id_bytes, root_hash_bytes
        )
        return web.json_response(
            {
                "root_changed": root_changed,
                "answer": answer,
            }
        )

    async def handle_operations(self, request: web.Request) -> web.Response:
        tree_id = request.rel_url.query["tree_id"]
        generation = request.rel_url.query["generation"]
        tree_id_bytes = bytes32.from_hexstr(tree_id)
        return web.json_response(await self.data_store.get_operations(tree_id_bytes, int(generation)))

    async def init_example_data_store(self) -> None:
        tree_id = bytes32(b"\0" * 32)
        await self.data_store.create_tree(tree_id=tree_id)
        await generate_big_datastore(data_store=self.data_store, tree_id=tree_id)
        print("Generated datastore.")

    async def start(self) -> web.Application:
        self.db_connection = await aiosqlite.connect(":memory:")
        await self.db_connection.execute("PRAGMA foreign_keys = ON")
        self.db_wrapper = DBWrapper(self.db_connection)
        self.data_store = await DataStore.create(db_wrapper=self.db_wrapper)
        await self.init_example_data_store()

        app = web.Application()
        app.add_routes(
            [
                web.get("/get_tree_root", self.handle_tree_root),
                web.get("/get_tree_nodes", self.handle_tree_nodes),
                web.get("/get_operations", self.handle_operations),
            ]
        )
        return app


if __name__ == "__main__":
    data_layer_server = DataLayerServer()
    web.run_app(data_layer_server.start())
