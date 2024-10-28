from aiogram.fsm.state import StatesGroup, State

# Состояния для входа 
class AuthState(StatesGroup):
    waiting_for_password = State()
    
# Состояния для регистрации
class RegistrationState(StatesGroup):
    waiting_for_fio = State()
    waiting_for_department = State()
    waiting_for_role = State()
    waiting_for_password = State()

class EditTaskState(StatesGroup):
    waiting_for_text = State()  # Ожидаем новый текст для напоминания
    waiting_for_task_id = State()  # Ожидаем ID напоминания для изменения

class DeleteTaskState(StatesGroup):
    waiting_for_accept = State()

class AddReminderState(StatesGroup):
    waiting_for_text = State()
    waiting_for_date = State()
    waiting_for_importance = State()

class AddReminderEmployeeState(StatesGroup):
    waiting_for_employee_text = State()
    waiting_for_employee_date = State()
    waiting_for_employee_importance = State()
    
