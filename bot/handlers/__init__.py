
from . import admin, commands  # импортируем модули-обработчики
from . import callbacks 

def register_all_handlers(dp):
    
    # Функция, которая регистрирует все обработчики из папки handlers

    admin.register_admin_handlers(dp)
    commands.register_commands_handlers(dp)
    callbacks.register_callbacks_handlers(dp)
 
