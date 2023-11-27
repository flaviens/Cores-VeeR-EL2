# Copyright (c) 2023 Antmicro <www.antmicro.com>
# SPDX-License-Identifier: Apache-2.0

import random

import pyuvm
from pyuvm import *

from cocotb.triggers import ClockCycles

from testbench import BaseEnv, BaseTest
from testbench import BusWriteItem, AXI4LiteResponseItem, AXI4LiteReadyItem

# =============================================================================

class AHBWriteSequence(uvm_sequence):
    """
    """

    def __init__(self, name):
        super().__init__(name)

    async def body(self):

        dwidth = 64
        align  = 8

        addr = 0xF0040000 + random.randrange(0, 0x1000)
        addr = (addr // align) * align
        data = [random.randrange(0, (1 << dwidth) - 1)]

        item = BusWriteItem(addr, data)
        await self.start_item(item)
        await self.finish_item(item)


class AXI4LiteWriteResponseSequence(uvm_sequence):
    """
    """

    def __init__(self, name):
        super().__init__(name)

    async def body(self):

        # Respond to AW and W
        item = AXI4LiteResponseItem(["aw", "w"])
        await self.start_item(item)
        await self.finish_item(item)

        # Emulate latency
        await ClockCycles(cocotb.top.clk, 2)

        # Respond on B
        item = AXI4LiteResponseItem(["b"])
        await self.start_item(item)
        await self.finish_item(item)

class AXI4LiteWriteReadySequence(uvm_sequence):
    """
    """

    def __init__(self, name):
        super().__init__(name)

    async def body(self):

        # Become ready
        item = AXI4LiteReadyItem(["aw", "w"], True)
        await self.start_item(item)
        await self.finish_item(item)


# =============================================================================

class NoBackpressureWriteSequence(uvm_sequence):

    async def body(self):
        ahb_seqr = ConfigDB().get(None, "", "AHB_SEQR")
        axi_seqr = ConfigDB().get(None, "", "AXI_SEQR")

        axi_rdy = AXI4LiteWriteReadySequence("ready")
        ahb_seq = AHBWriteSequence("stimulus")
        axi_seq = AXI4LiteWriteResponseSequence("response")

        # Issue am AHB write and do a correct AXI response
        await axi_rdy.start(axi_seqr)
        await ahb_seq.start(ahb_seqr)
        await axi_seq.start(axi_seqr)


class BackpressureWriteSequence(uvm_sequence):

    async def body(self):
        ahb_seqr = ConfigDB().get(None, "", "AHB_SEQR")
        axi_seqr = ConfigDB().get(None, "", "AXI_SEQR")

        ahb_seq = AHBWriteSequence("stimulus")
        axi_seq = AXI4LiteWriteResponseSequence("response")

        # Issue am AHB write and do a correct AXI response
        await ahb_seq.start(ahb_seqr)
        await axi_seq.start(axi_seqr)

# =============================================================================

@pyuvm.test()
class TestWriteNoBackpressure(BaseTest):
    """
    Write test with no AXI backpressure
    """

    def end_of_elaboration_phase(self):
        super().end_of_elaboration_phase()
        self.seq = NoBackpressureWriteSequence()

    async def run(self):

        count = ConfigDB().get(None, "", "TEST_ITERATIONS")
        gap   = ConfigDB().get(None, "", "TEST_BURST_GAP")

        for i in range(count):
            await self.seq.start()
            await ClockCycles(cocotb.top.clk, gap)

@pyuvm.test()
class TestWriteBackpressure(BaseTest):
    """
    Write test with AXI backpressure
    """

    def end_of_elaboration_phase(self):
        super().end_of_elaboration_phase()
        self.seq = BackpressureWriteSequence()

    async def run(self):

        count = ConfigDB().get(None, "", "TEST_ITERATIONS")
        gap   = ConfigDB().get(None, "", "TEST_BURST_GAP")

        for i in range(count):
            await self.seq.start()
            await ClockCycles(cocotb.top.clk, gap)

