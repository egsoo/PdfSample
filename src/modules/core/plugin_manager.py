from typing import Any, ClassVar, cast

import regex as re
from telethon import Button
from telethon.events import CallbackQuery, NewMessage
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopePeer

from src.modules.base import ModuleBase
from src.utils.command import Command
from src.utils.filters import is_admin_in_private
from src.utils.i18n import t


async def list_plugins(event: NewMessage.Event) -> None:
    modules_registry = event.client.modules_registry
    enabled_modules = []
    disabled_modules = []

    for module in modules_registry.modules:
        enabled_modules.append(module.name) if modules_registry.modules_status.get(
            module.name, True
        ) else disabled_modules.append(module.name)

    enabled_text = ', '.join(sorted(enabled_modules)) if enabled_modules else 'None'
    disabled_text = ', '.join(sorted(disabled_modules)) if disabled_modules else 'None'
    await event.reply(
        f'<b>{t("enabled_modules")}</b>: {enabled_text}\n'
        f'<b>{t("disabled_modules")}</b>: {disabled_text}',
    )


async def list_commands(event: NewMessage.Event) -> None:
    modules_registry = event.client.modules_registry
    all_commands: dict[str, ModuleBase.CommandsT] = modules_registry.get_all_commands(event)
    await event.reply(help_menu_text(), buttons=help_menu_buttons())
    # Set bot commands
    await event.client(
        SetBotCommandsRequest(
            scope=BotCommandScopePeer(event.input_chat),
            lang_code='',
            commands=[
                BotCommand(command_name, command_data.description)
                for module_commands in all_commands.values()
                for command_name, command_data in module_commands.items()
                if ' ' not in command_name
            ],
        )
    )


HELP_CATEGORIES: tuple[tuple[str, str], ...] = (
    ('audio', '🎵 Audio'),
    ('media', '🎬 Media'),
    ('pdf', '📄 PDF'),
    ('ocr', '📝 OCR'),
    ('youtube', '📥 YouTube'),
    ('tools', '🔗 Tools'),
    ('system', '🛠️ System'),
    ('upload', '📤 Upload'),
)


def help_menu_text() -> str:
    return '🤖 Telegram Utils Bot\n\nChoose what you want to do:'


def start_menu_text() -> str:
    return '👋 Welcome to Telegram Utils Bot!\n\nChoose what you want to do:'


def category_buttons(origin: str) -> list[list[Button]]:
    buttons = [
        Button.inline(label, data=f'h|category|{category}|{origin}')
        for category, label in HELP_CATEGORIES
    ]
    return [buttons[index : index + 2] for index in range(0, len(buttons), 2)]


def help_menu_buttons() -> list[list[Button]]:
    buttons = category_buttons('commands')
    buttons.append([Button.inline('‹ Back', data='h|start')])
    return buttons


def start_menu_buttons() -> list[list[Button]]:
    return [[
        Button.inline('📋 Commands', data='h|commands'),
        Button.inline('ℹ️ About', data='h|about'),
    ]]


def command_category(command: str) -> str:
    """Return the help category for a command without changing command routing."""
    if command.startswith(('audio ', 'voice', 'transcribe', 'gemini transcribe')):
        return 'audio'
    if command.startswith(('media ', 'video ', 'image convert', 'image trim')):
        return 'media'
    if command == 'pdf' or (command.startswith('pdf ') and command != 'pdf ocr'):
        return 'pdf'
    if command in {'ocr', 'pdf ocr', 'screenai ocr', 'image ocr', 'gemini ocr'}:
        return 'ocr'
    if command.startswith(('youtube', 'yt')):
        return 'youtube'
    if command in {'download', 'upload', 'gdrive'} or command.startswith('upload '):
        return 'upload'
    if command in {
        'plugins',
        'commands',
        'help',
        'plugins enable',
        'plugins disable',
        'tasks',
        'tasks cancel',
        'permissions',
        'permissions add',
        'permissions remove',
        'users',
        'restart',
        'update',
        'broadcast',
        'shell',
        'exec',
        'ping',
    }:
        return 'system'
    return 'tools'


def commands_for_category(
    all_commands: dict[str, ModuleBase.CommandsT], category: str
) -> list[tuple[str, str]]:
    return [
        (command, data.description)
        for commands in all_commands.values()
        for command, data in commands.items()
        if command_category(command) == category
    ]


def category_help_text(category: str, commands: list[tuple[str, str]]) -> str:
    label = dict(HELP_CATEGORIES)[category]
    lines = [f'<b>{label}</b>', '']
    command_lines = [f'<u>/{command}</u>: {description}' for command, description in commands]
    lines.append('\n\n'.join(command_lines))
    return '\n'.join(lines)


def category_help_buttons(commands: list[tuple[str, str]], origin: str) -> list[list[Button]]:
    back_target = 'h|start' if origin == 'start' else 'h|commands'
    return [[Button.inline('‹ Back', data=back_target)]]


async def handle_help_callback(event: CallbackQuery.Event) -> None:
    data = event.data.decode('utf-8', errors='ignore')
    if data in {'h|commands', 'h|main'}:
        await event.edit(help_menu_text(), buttons=help_menu_buttons())
    elif data == 'h|start':
        await event.edit(start_menu_text(), buttons=start_menu_buttons())
    elif data == 'h|about':
        await event.edit(
            'ℹ️ <b>About Telegram Utils Bot</b>\n\n'
            'A multipurpose bot for audio, media, PDF, OCR, YouTube, and file tools.',
            buttons=[[Button.inline('‹ Back', data='h|start')]],
        )
    else:
        parts = data.split('|')
        category = parts[2] if len(parts) > 2 else ''
        origin = parts[3] if len(parts) > 3 else 'main'
        if category not in dict(HELP_CATEGORIES):
            return
        all_commands = event.client.modules_registry.get_all_commands(
            cast(NewMessage.Event, event)
        )
        commands = commands_for_category(all_commands, category)
        await event.edit(
            category_help_text(category, commands),
            buttons=category_help_buttons(commands, origin),
        )
    await event.answer()


async def manage_plugins(event: NewMessage.Event) -> None:
    modules_registry = event.client.modules_registry
    action, module_name = event.message.text.split('plugins ')[1].split(' ')
    if action == 'enable':
        modules_registry.enable_module(module_name)
        await event.reply(t('module_enabled', module_name=module_name))
    if action == 'disable':
        modules_registry.disable_module(module_name)
        await event.reply(t('module_disabled', module_name=module_name))


class PluginManager(ModuleBase):
    name = 'Plugin Manager'
    description = t('_plugins_module_description')
    commands: ClassVar[ModuleBase.CommandsT] = {
        'plugins': Command(
            handler=list_plugins,
            description=t('_plugins_description'),
            pattern=re.compile(r'^/plugins$'),
            condition=is_admin_in_private,
        ),
        'commands': Command(
            handler=list_commands,
            description=t('_commands_description'),
            pattern=re.compile(r'^/(commands|help)$'),
            condition=is_admin_in_private,
        ),
        'help': Command(
            handler=list_commands,
            description=t('_commands_description'),
            pattern=re.compile(r'^/(commands|help)$'),
            condition=is_admin_in_private,
        ),
        'plugins enable': Command(
            handler=manage_plugins,
            description=t('_plugins_enable_description'),
            pattern=re.compile(r'^/plugins\s+enable\s+(\w+)$'),
            condition=is_admin_in_private,
        ),
        'plugins disable': Command(
            handler=manage_plugins,
            description=t('_plugins_disable_description'),
            pattern=re.compile(r'^/plugins\s+disable\s+(\w+)$'),
            condition=is_admin_in_private,
        ),
    }

    @staticmethod
    def register_handlers(bot: Any) -> None:
        bot.add_event_handler(handle_help_callback, CallbackQuery(pattern=r'^h\|'))
