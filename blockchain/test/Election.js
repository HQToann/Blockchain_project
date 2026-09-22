import { expect } from "chai";
import pkg from 'hardhat';
const { ethers } = pkg;

describe("Election Smart Contract", function () {
  let election;
  let owner;
  let addr1;
  let addr2;

  beforeEach(async function () {
    [owner, addr1, addr2] = await ethers.getSigners();
    
    const ElectionFactory = await ethers.getContractFactory("Election");
    // Deploy hòm phiếu Private để test Whitelist luôn
    election = await ElectionFactory.deploy(owner.address, "Test Election", true); 
  });

  it("Nên block vote khi hòm phiếu chưa mở", async function () {
    await election.addCandidate("Alice");
    await expect(election.connect(addr1).vote(0)).to.be.revertedWith("Loi: Hom phieu chua mo hoac da dong");
  });

  it("Nên cho phép vote khi đã mở, người dùng trong whitelist, và block vote 2 lần", async function () {
    await election.addCandidate("Alice");
    await election.addToWhitelist([addr1.address]);
    await election.startElection();
    
    // Lần 1: Vote thành công — VoteCast giờ có thêm voter address
    await expect(election.connect(addr1).vote(0))
      .to.emit(election, "VoteCast")
      .withArgs(addr1.address, 0);  // Updated: thêm voter address

    const candidate = await election.candidates(0);
    expect(candidate.voteCount).to.equal(1n);
    
    // Lần 2: Vote lại sẽ bị block
    await expect(election.connect(addr1).vote(0)).to.be.revertedWith("Loi: Ban da bo phieu roi");
  });

  it("Nên chặn người không có trong whitelist (isPrivate = true)", async function () {
    await election.addCandidate("Bob");
    await election.startElection();
    
    // addr1 không có trong whitelist -> Revert
    await expect(election.connect(addr1).vote(0)).to.be.revertedWith("Loi: Ban khong co trong danh sach Whitelist");
  });

  it("Nên block vote khi hòm phiếu đã đóng", async function () {
    await election.addCandidate("Charlie");
    await election.addToWhitelist([addr1.address]);
    await election.startElection();
    
    await election.stopElection();
    
    await expect(election.connect(addr1).vote(0)).to.be.revertedWith("Loi: Hom phieu chua mo hoac da dong");
  });

  it("ElectionStatusChanged event nên phát đúng khi mở/đóng", async function () {
    await expect(election.startElection())
      .to.emit(election, "ElectionStatusChanged")
      .withArgs(true);

    await expect(election.stopElection())
      .to.emit(election, "ElectionStatusChanged")
      .withArgs(false);
  });

  it("VoterAddedToWhitelist event nên phát đúng khi thêm whitelist", async function () {
    await expect(election.addToWhitelist([addr1.address, addr2.address]))
      .to.emit(election, "VoterAddedToWhitelist")
      .withArgs(addr1.address);
  });
});
