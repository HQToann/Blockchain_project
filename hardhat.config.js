import "@nomicfoundation/hardhat-toolbox";
import "dotenv/config";

export default {
  solidity: "0.8.20",
  paths: {
    sources:   "./blockchain/contracts",  // Đã di chuyển vào thư mục blockchain/
    tests:     "./blockchain/test",
    ignition:  "./blockchain/ignition",
    cache:     "./cache",
    artifacts: "./artifacts",
  },
  networks: {
    sepolia: {
      url: process.env.ALCHEMY_RPC_URL || "",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
    },
  },
};
