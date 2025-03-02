# TODO: #445 Add example for grok *NOT WORKING YET - this needs updating*

import asyncio

from pydantic import BaseModel, Field
from traitlets import Callable

from beeai_framework.adapters.xai.backend.chat import xAIChatModel
from beeai_framework.backend.chat import ChatModel, ChatModelOutput
from beeai_framework.backend.message import UserMessage
from beeai_framework.cancellation import AbortSignal
from beeai_framework.emitter import EventMeta
from beeai_framework.errors import AbortError
from beeai_framework.parsers.field import ParserField
from beeai_framework.parsers.line_prefix import LinePrefixParser, LinePrefixParserNode


async def xai_from_name() -> None:
    llm = ChatModel.from_name("xai:grok-2")
    user_message = UserMessage("what states are part of New England?")
    response = await llm.create(messages=[user_message])
    print(response.get_text_content())


# TODO: #445 The naming makes no sense here
async def xai_granite_from_name() -> None:
    llm = ChatModel.from_name("xai:grok-2")
    user_message = UserMessage("what states are part of New England?")
    response = await llm.create(messages=[user_message])
    print(response.get_text_content())


async def xai_sync() -> None:
    llm = xAIChatModel("grok-2")
    user_message = UserMessage("what is the capital of Massachusetts?")
    response = await llm.create(messages=[user_message])
    print(response.get_text_content())


async def xai_stream() -> None:
    llm = xAIChatModel("grok-2")
    user_message = UserMessage("How many islands make up the country of Cape Verde?")
    response = await llm.create(messages=[user_message], stream=True)
    print(response.get_text_content())


async def xai_stream_abort() -> None:
    llm = xAIChatModel("grok-2")
    user_message = UserMessage("What is the smallest of the Cape Verde islands?")

    try:
        response = await llm.create(messages=[user_message], stream=True, abort_signal=AbortSignal.timeout(0.5))

        if response is not None:
            print(response.get_text_content())
        else:
            print("No response returned.")
    except AbortError as err:
        print(f"Aborted: {err}")


async def xai_structure() -> None:
    class TestSchema(BaseModel):
        answer: str = Field(description="your final answer")

    llm = xAIChatModel("grok-2")
    user_message = UserMessage("How many islands make up the country of Cape Verde?")
    response = await llm.create_structure(
        {
            "schema": TestSchema,
            "messages": [user_message],
        }
    )
    print(response.object)


async def xai_stream_parser() -> None:
    llm = xAIChatModel("grok-2")

    parser = LinePrefixParser(
        nodes={
            "test": LinePrefixParserNode(
                prefix="Prefix: ",
                field=ParserField.from_type(str),
                is_start=True,
                is_end=True,
            )
        }
    )

    async def on_new_token(value: tuple[ChatModelOutput, Callable], event: EventMeta) -> None:
        data, abort = value
        await parser.add(data.get_text_content())

    user_message = UserMessage("Produce 3 lines each starting with 'Prefix: ' followed by a sentence and a new line.")
    await llm.create(messages=[user_message], stream=True).observe(lambda emitter: emitter.on("newToken", on_new_token))
    result = await parser.end()
    print(result)


async def main() -> None:
    print("*" * 10, "xai_from_name")
    await xai_from_name()
    print("*" * 10, "xai_granite_from_name")
    await xai_granite_from_name()
    print("*" * 10, "xai_sync")
    await xai_sync()
    print("*" * 10, "xai_stream")
    await xai_stream()
    print("*" * 10, "xai_stream_abort")
    await xai_stream_abort()
    # TODO #445 currently fails with xai - check openai
    #print("*" * 10, "xai_structure")
    #await xai_structure()
    print("*" * 10, "xai_stream_parser")
    await xai_stream_parser()


if __name__ == "__main__":
    asyncio.run(main())
