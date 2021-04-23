import tempfile
from os.path import basename
from zipfile import ZipFile
import configparser

from garnet import ctx
from garnet.runner import RuntimeConfig
from garnet.runner import run
from garnet.filters import text, State, group
from garnet.storages import DictStorage
from garnet.events import Router

router = Router()

class States(group.Group):
    state_waiting = group.M()
    state_uploading = group.M()
    state_naming = group.M()

@router.use()
async def only_pm(handler, event):
    if event.is_private:
        try:
            return await handler(event)
        except Exception as e:
            print("Error happened", e)
            await event.reply(f"An error happened please retry:\nerror code : {e}")
            fsm = ctx.CageCtx.get()
            await fsm.set_state(States.state_waiting)
            await fsm.set_data({"files": []})

@router.message(text.commands("start", prefixes="/") & (State.exact(States.state_waiting) | State.entry))
async def response(event):
    await event.reply("Hi ! I\'m Archiver Bot.\n\n**HOW TO USE** :\n1. Send Me Multiple Files.\n2. When You Finished Send /done.\n3. Send a Filename but Without Extension For Ex. Pics\n4. I'll Archive All Your Files & Send To You.\n\n**NOTE** :\nI'll Didn't Save Any Kind Of Your data File,\nI'll Instantly Delete All Yours Sent File After Archive Process.")
    fsm = ctx.CageCtx.get()
    await fsm.set_state(States.state_uploading)
    await fsm.set_data({"files": []})

@router.message(State.exact(States.state_waiting) | State.entry)
async def response(event):
    await event.reply("Send /start to Initiate Process")

@router.message(text.commands("done", prefixes="/") & State.exact(States.state_uploading))
async def finished(event):
    fsm = ctx.CageCtx.get()
    await fsm.set_state(States.state_naming)
    await event.reply("Please Send Name for Archive File.l")

@router.message(State.exact(States.state_naming))
async def naming(event):
    fsm = ctx.CageCtx.get()
    await fsm.set_state(States.state_waiting)
    data = await fsm.get_data()
    files = data['files']
    msg = await event.reply("Downloading...")

    with tempfile.TemporaryDirectory() as tmp_dirname:
        with ZipFile(f'{tmp_dirname}/{event.text}.zip', 'w') as zipObj2:
            for file in files:
                path = await event.client.download_media(file, file=tmp_dirname)
                zipObj2.write(path, basename(path))
        await msg.edit(f"Uploading Archive With {len(files)} Files.")
        await event.reply(file=f'{tmp_dirname}/{event.text}.zip')
    await fsm.set_data({"files": []})

@router.message(State.exact(States.state_uploading))
async def uploading(event):
    if event.file:
        fsm = ctx.CageCtx.get()
        data = await fsm.get_data()
        files = data['files']
        files.append(event.message.media)
        await fsm.set_data(data)
        await event.reply(f"Received {len(files)} File.\nSend More Files else /done If You've Finished.")
     else:
        await event.reply("Please Send Files or /done To Finish.")

def default_conf_maker() -> RuntimeConfig:
    config = configparser.ConfigParser()
    config.read('config.ini')
    default = config['DEFAULT']
    return RuntimeConfig(
        bot_token=default["bot_token"],
        app_id=default["app_id"],
        app_hash=default["app_hash"],
        session_dsn=default["session_dsn"],
    )

async def main():
    main_router = Router().include(router)
    await run(main_router, DictStorage(), conf_maker=default_conf_maker)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
