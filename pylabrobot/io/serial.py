import logging
from io import IOBase
from typing import Optional

try:
  import serial

  HAS_SERIAL = True
except ImportError:
  HAS_SERIAL = False

from pylabrobot.io.validation_utils import LOG_LEVEL_IO, ValidationError, align_sequences

logger = logging.getLogger(__name__)


class Serial(IOBase):
  """Thin wrapper around serial.Serial to include PLR logging (for io testing)."""

  def __init__(
    self,
    port: str,
    baudrate: int = 9600,
    bytesize: int = serial.EIGHTBITS,
    parity: str = serial.PARITY_NONE,
    stopbits: int = serial.STOPBITS_ONE,
    write_timeout=1,
    timeout=1,
  ):
    self._port = port
    self.baudrate = baudrate
    self.bytesize = bytesize
    self.parity = parity
    self.stopbits = stopbits
    self.ser: Optional[serial.Serial] = None
    self.write_timeout = write_timeout
    self.timeout = timeout

  async def setup(self):
    if not HAS_SERIAL:
      raise RuntimeError("pyserial not installed.")

    try:
      self.ser = serial.Serial(
        port=self._port,
        baudrate=self.baudrate,
        bytesize=self.bytesize,
        parity=self.parity,
        stopbits=self.stopbits,
        write_timeout=self.write_timeout,
        timeout=self.timeout,
      )
    except serial.SerialException as e:
      logger.error("Could not connect to device, is it in use by a different notebook/process?")
      raise e

  async def stop(self):
    if self.ser.is_open:
      self.ser.close()

  async def write(self, data: bytes):
    logger.log(LOG_LEVEL_IO, "[%s] write %s", self._port, data)
    self.ser.write(data)

  async def read(self, num_bytes: int = 1) -> bytes:
    data = self.ser.read(num_bytes)
    logger.log(LOG_LEVEL_IO, "[%s] read %s", self._port, data)
    return data

  async def readline(self) -> bytes:
    data = self.ser.readline()
    logger.log(LOG_LEVEL_IO, "[%s] readline %s", self._port, data)
    return data


class SerialValidator(Serial):
  def __init__(
    self,
    lr,
    port: str,
    baudrate: int = 9600,
    bytesize: int = serial.EIGHTBITS,
    parity: str = serial.PARITY_NONE,
    stopbits: int = serial.STOPBITS_ONE,
  ):
    super().__init__(
      port=port,
      baudrate=baudrate,
      bytesize=bytesize,
      parity=parity,
      stopbits=stopbits,
    )
    self.lr = lr

  async def setup(self):
    pass

  def write(self, data: bytes):
    next_line = self.lr.next_line()
    port, action, log_data = next_line.split(" ", 2)
    action = action.rstrip(":")

    if not port == self._port:
      raise ValidationError(
        f"next command is sent to device with port {port}, expected {self._port}"
      )

    if not action == "write":
      raise ValidationError(f"next command is {action}, expected 'write'")

    if not log_data == data:
      align_sequences(expected=log_data, actual=data)
      raise ValidationError("Data mismatch: difference was written to stdout.")

  def read(self, num_bytes: int) -> bytes:
    next_line = self.lr.next_line()
    port, action, log_data = next_line.split(" ", 2)
    action = action.rstrip(":")  # remove the colon at the end

    if not port == self._port:
      raise ValidationError(
        f"next command is sent to device with port {port}, expected {self._port}"
      )

    if not action == "read":
      raise ValidationError(f"next command is {action}, expected 'read'")

    if not len(log_data) == num_bytes:
      raise ValidationError(f"Expected to read {num_bytes} bytes, got {len(log_data)} bytes")

    return log_data.encode()

  def readline(self) -> bytes:
    next_line = self.lr.next_line()
    port, action, log_data = next_line.split(" ", 2)
    action = action.rstrip(":")  # remove the colon at the end

    if not port == self._port:
      raise ValidationError(
        f"next command is sent to device with port {port}, expected {self._port}"
      )

    if not action == "readline":
      raise ValidationError(f"next command is {action}, expected 'readline'")

    return log_data.encode()
