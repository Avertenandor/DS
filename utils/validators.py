"""
Модуль: Валидаторы данных для PLEX Dynamic Staking Manager
Описание: Валидация адресов, транзакций, балансов и других данных блокчейна
Зависимости: web3, decimal
Автор: GitHub Copilot
"""

import re
from decimal import Decimal
from typing import Union, List, Dict, Optional, Tuple
from web3 import Web3

from config.constants import TOKEN_DECIMALS, MIN_BALANCE
from utils.logger import get_logger

logger = get_logger("Validators")


class ValidationError(Exception):
    """Ошибка валидации данных"""
    pass


class AddressValidator:
    """Валидатор Ethereum/BSC адресов"""
    
    @staticmethod
    def is_valid_address(address: str) -> bool:
        """Проверить корректность адреса"""
        if not isinstance(address, str):
            return False
        
        # Проверка формата 0x + 40 hex символов
        if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
            return False
        
        # Проверка checksum (если применяется)
        try:
            return Web3.is_address(address)
        except Exception:
            return False
    
    @staticmethod
    def normalize_address(address: str) -> str:
        """Нормализовать адрес к checksum формату"""
        if not AddressValidator.is_valid_address(address):
            raise ValidationError(f"Invalid address format: {address}")
        
        return Web3.to_checksum_address(address)
    
    @staticmethod
    def validate_address_list(addresses: List[str]) -> List[str]:
        """Валидировать и нормализовать список адресов"""
        validated = []
        for addr in addresses:
            try:
                normalized = AddressValidator.normalize_address(addr)
                validated.append(normalized)
            except ValidationError as e:
                logger.warning(f"⚠️ Skipping invalid address {addr}: {e}")
                continue
        
        return validated
    
    @staticmethod
    def is_zero_address(address: str) -> bool:
        """Проверить, является ли адрес нулевым"""
        try:
            normalized = AddressValidator.normalize_address(address)
            return normalized == "0x0000000000000000000000000000000000000000"
        except ValidationError:
            return False


class TransactionValidator:
    """Валидатор транзакций"""
    
    @staticmethod
    def is_valid_tx_hash(tx_hash: str) -> bool:
        """Проверить корректность хэша транзакции"""
        if not isinstance(tx_hash, str):
            return False
        
        # Проверка формата 0x + 64 hex символа
        return bool(re.match(r'^0x[a-fA-F0-9]{64}$', tx_hash))
    
    @staticmethod
    def validate_tx_hash(tx_hash: str) -> str:
        """Валидировать и нормализовать хэш транзакции"""
        if not TransactionValidator.is_valid_tx_hash(tx_hash):
            raise ValidationError(f"Invalid transaction hash: {tx_hash}")
        
        return tx_hash.lower()
    
    @staticmethod
    def validate_block_number(block_number: Union[int, str]) -> int:
        """Валидировать номер блока"""
        try:
            block_num = int(block_number)
            if block_num < 0:
                raise ValidationError(f"Block number cannot be negative: {block_num}")
            return block_num
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid block number format: {block_number}")
    
    @staticmethod
    def validate_block_range(start_block: int, end_block: int) -> Tuple[int, int]:
        """Валидировать диапазон блоков"""
        start = TransactionValidator.validate_block_number(start_block)
        end = TransactionValidator.validate_block_number(end_block)
        
        if start > end:
            raise ValidationError(f"Start block {start} cannot be greater than end block {end}")
        
        return start, end


class BalanceValidator:
    """Валидатор балансов и сумм"""
    
    @staticmethod
    def validate_token_amount(amount: Union[str, int, float, Decimal], 
                            allow_zero: bool = True) -> Decimal:
        """Валидировать количество токенов"""
        try:
            decimal_amount = Decimal(str(amount))
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid amount format: {amount}")
        
        if decimal_amount < 0:
            raise ValidationError(f"Amount cannot be negative: {amount}")
        
        if not allow_zero and decimal_amount == 0:
            raise ValidationError(f"Amount cannot be zero: {amount}")
        
        # Проверка на слишком большое количество знаков после запятой
        if decimal_amount.as_tuple().exponent < -TOKEN_DECIMALS:
            raise ValidationError(f"Too many decimal places for token: {amount}")
        
        return decimal_amount
    
    @staticmethod
    def validate_wei_amount(wei_amount: Union[str, int]) -> int:
        """Валидировать количество в Wei"""
        try:
            wei = int(wei_amount)
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid Wei amount format: {wei_amount}")
        
        if wei < 0:
            raise ValidationError(f"Wei amount cannot be negative: {wei}")
        
        return wei
    
    @staticmethod
    def wei_to_token(wei_amount: Union[str, int]) -> Decimal:
        """Конвертировать Wei в токены с валидацией"""
        wei = BalanceValidator.validate_wei_amount(wei_amount)
        return Decimal(wei) / Decimal(10 ** TOKEN_DECIMALS)
    
    @staticmethod
    def token_to_wei(token_amount: Union[str, float, Decimal]) -> int:
        """Конвертировать токены в Wei с валидацией"""
        amount = BalanceValidator.validate_token_amount(token_amount)
        wei = int(amount * Decimal(10 ** TOKEN_DECIMALS))
        return wei
    
    @staticmethod
    def is_eligible_balance(balance: Union[str, float, Decimal]) -> bool:
        """Проверить, достаточен ли баланс для участия"""
        try:
            amount = BalanceValidator.validate_token_amount(balance)
            return amount >= Decimal(str(MIN_BALANCE))
        except ValidationError:
            return False


class SwapDataValidator:
    """Валидатор данных swap операций"""
    
    @staticmethod
    def validate_swap_amounts(amount0_in: int, amount1_in: int, 
                            amount0_out: int, amount1_out: int) -> bool:
        """Валидировать суммы swap операции"""
        # Один из входящих должен быть больше 0
        if amount0_in == 0 and amount1_in == 0:
            return False
        
        # Один из исходящих должен быть больше 0
        if amount0_out == 0 and amount1_out == 0:
            return False
        
        # Не должно быть одновременного входа и выхода одного токена
        if amount0_in > 0 and amount0_out > 0:
            return False
        
        if amount1_in > 0 and amount1_out > 0:
            return False
        
        return True
    
    @staticmethod
    def determine_swap_direction(amount0_in: int, amount1_in: int, 
                               amount0_out: int, amount1_out: int,
                               token0_is_plex: bool) -> str:
        """Определить направление swap (buy/sell)"""
        if not SwapDataValidator.validate_swap_amounts(amount0_in, amount1_in, amount0_out, amount1_out):
            raise ValidationError("Invalid swap amounts")
        
        if token0_is_plex:
            # Token0 = PLEX, Token1 = USDT
            if amount0_out > 0:  # PLEX выходит -> покупка PLEX
                return "buy"
            else:  # PLEX входит -> продажа PLEX
                return "sell"
        else:
            # Token0 = USDT, Token1 = PLEX
            if amount1_out > 0:  # PLEX выходит -> покупка PLEX
                return "buy"
            else:  # PLEX входит -> продажа PLEX
                return "sell"
    
    @staticmethod
    def calculate_usd_value(amount0_in: int, amount1_in: int,
                          amount0_out: int, amount1_out: int,
                          token0_is_usdt: bool) -> Decimal:
        """Рассчитать USD стоимость swap операции"""
        usdt_decimals = 18
        
        if token0_is_usdt:
            # Token0 = USDT
            usdt_amount = amount0_in if amount0_in > 0 else amount0_out
        else:
            # Token1 = USDT
            usdt_amount = amount1_in if amount1_in > 0 else amount1_out
        
        return Decimal(usdt_amount) / Decimal(10 ** usdt_decimals)


class TimeValidator:
    """Валидатор временных данных"""
    
    @staticmethod
    def validate_timestamp(timestamp: Union[int, float]) -> int:
        """Валидировать Unix timestamp"""
        try:
            ts = int(timestamp)
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid timestamp format: {timestamp}")
        
        if ts < 0:
            raise ValidationError(f"Timestamp cannot be negative: {ts}")
        
        # Проверка разумности timestamp (не в далеком прошлом/будущем)
        import time
        current_time = int(time.time())
        
        # Не раньше 2020 года и не позже чем через год
        if ts < 1577836800 or ts > current_time + 31536000:
            raise ValidationError(f"Timestamp out of reasonable range: {ts}")
        
        return ts
    
    @staticmethod
    def validate_date_range(start_timestamp: int, end_timestamp: int) -> Tuple[int, int]:
        """Валидировать диапазон дат"""
        start = TimeValidator.validate_timestamp(start_timestamp)
        end = TimeValidator.validate_timestamp(end_timestamp)
        
        if start >= end:
            raise ValidationError(f"Start timestamp {start} must be before end timestamp {end}")
        
        return start, end


class APIDataValidator:
    """Валидатор данных API"""
    
    @staticmethod
    def validate_log_entry(log_entry: Dict) -> bool:
        """Валидировать запись лога из блокчейна"""
        required_fields = ['address', 'topics', 'data', 'blockNumber', 'transactionHash']
        
        for field in required_fields:
            if field not in log_entry:
                logger.warning(f"⚠️ Missing required field in log entry: {field}")
                return False
        
        # Валидация конкретных полей
        try:
            AddressValidator.validate_address(log_entry['address'])
            TransactionValidator.validate_tx_hash(log_entry['transactionHash'])
            TransactionValidator.validate_block_number(log_entry['blockNumber'])
        except ValidationError as e:
            logger.warning(f"⚠️ Invalid log entry data: {e}")
            return False
        
        return True
    
    @staticmethod
    def validate_multicall_result(result: List) -> bool:
        """Валидировать результат multicall операции"""
        if not isinstance(result, list):
            return False
        
        for item in result:
            if not isinstance(item, dict) or 'success' not in item or 'returnData' not in item:
                return False
        
        return True


def validate_plex_transfer_data(from_addr: str, to_addr: str, value: int) -> Dict:
    """Комплексная валидация данных перевода PLEX"""
    try:
        # Валидация адресов
        from_normalized = AddressValidator.normalize_address(from_addr)
        to_normalized = AddressValidator.normalize_address(to_addr)
        
        # Валидация суммы
        wei_amount = BalanceValidator.validate_wei_amount(value)
        token_amount = BalanceValidator.wei_to_token(wei_amount)
        
        # Проверки безопасности
        if AddressValidator.is_zero_address(from_normalized):
            logger.warning(f"⚠️ Transfer from zero address detected")
        
        if AddressValidator.is_zero_address(to_normalized):
            logger.warning(f"⚠️ Transfer to zero address detected")
        
        return {
            "valid": True,
            "from_address": from_normalized,
            "to_address": to_normalized,
            "wei_amount": wei_amount,
            "token_amount": token_amount,
            "is_eligible_amount": token_amount >= Decimal(str(MIN_BALANCE))
        }
        
    except ValidationError as e:
        logger.error(f"❌ PLEX transfer validation failed: {e}")
        return {
            "valid": False,
            "error": str(e)
        }


# Функции-обертки для удобства импорта
def validate_address(address: str) -> str:
    """Валидировать и нормализовать адрес"""
    return AddressValidator.normalize_address(address)

def is_valid_address(address: str) -> bool:
    """Проверить корректность адреса"""
    return AddressValidator.is_valid_address(address)

def validate_transaction_hash(tx_hash: str) -> str:
    """Валидировать хеш транзакции"""
    return TransactionValidator.validate_tx_hash(tx_hash)

def validate_token_amount(amount: Union[str, float, Decimal]) -> Decimal:
    """Валидировать количество токенов"""
    return BalanceValidator.validate_token_amount(amount)

def validate_swap_amounts(token0_in: int, token1_in: int, token0_out: int, token1_out: int) -> bool:
    """Валидировать данные swap"""
    return SwapDataValidator.validate_swap_amounts(token0_in, token1_in, token0_out, token1_out)


if __name__ == "__main__":
    # Тестирование валидаторов
    
    # Тест адресов
    valid_addr = "0xdf179b6cAdBC61FFD86A3D2e55f6d6e083ade6c1"
    invalid_addr = "0xinvalid"
    
    print(f"✅ Valid address: {AddressValidator.is_valid_address(valid_addr)}")
    print(f"❌ Invalid address: {AddressValidator.is_valid_address(invalid_addr)}")
    
    # Тест балансов
    try:
        amount = BalanceValidator.validate_token_amount("100.123456789")
        print(f"✅ Valid amount: {amount}")
        
        wei = BalanceValidator.token_to_wei(amount)
        back_to_token = BalanceValidator.wei_to_token(wei)
        print(f"✅ Wei conversion: {amount} -> {wei} -> {back_to_token}")
        
    except ValidationError as e:
        print(f"❌ Amount validation error: {e}")
    
    # Тест swap данных
    swap_valid = SwapDataValidator.validate_swap_amounts(0, 1000, 500, 0)
    print(f"✅ Swap amounts valid: {swap_valid}")
    
    direction = SwapDataValidator.determine_swap_direction(0, 1000, 500, 0, True)
    print(f"✅ Swap direction: {direction}")
    
    print("✅ Все валидаторы протестированы")
