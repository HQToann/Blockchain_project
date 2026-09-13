// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Election {
    string public electionName;
    address public admin;
    bool public isPrivate;
    bool public isOpen;

    struct Candidate {
        uint256 id;
        uint256 voteCount;
    }
    
    mapping(uint256 => Candidate) public candidates;
    uint256 public candidatesCount;
    
    mapping(address => bool) public hasVoted;
    mapping(address => bool) public whitelist;

    event VoteCast(uint256 indexed candidateId);
    event CandidateAdded(uint256 indexed candidateId, string name);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Loi: Chi Admin moi duoc thuc hien");
        _;
    }

    modifier onlyWhileOpen() {
        require(isOpen, "Loi: Hom phieu chua mo hoac da dong");
        _;
    }

    constructor(address _admin, string memory _name, bool _isPrivate) {
        admin = _admin;
        electionName = _name;
        isPrivate = _isPrivate;
        isOpen = false;
    }

    function addCandidate(string memory _name) public onlyAdmin {
        require(!isOpen, "Loi: Khong the them ung vien khi hom phieu dang mo");
        candidates[candidatesCount] = Candidate(candidatesCount, 0);
        emit CandidateAdded(candidatesCount, _name);
        candidatesCount++;
    }

    function addToWhitelist(address[] memory _voters) public onlyAdmin {
        for(uint i = 0; i < _voters.length; i++) {
            whitelist[_voters[i]] = true;
        }
    }

    function startElection() public onlyAdmin {
        isOpen = true;
    }

    function stopElection() public onlyAdmin {
        isOpen = false;
    }

    function vote(uint256 _candidateId) public onlyWhileOpen {
        require(!hasVoted[msg.sender], "Loi: Ban da bo phieu roi");
        require(_candidateId < candidatesCount, "Loi: Ung vien khong ton tai");
        
        if (isPrivate) {
            require(whitelist[msg.sender], "Loi: Ban khong co trong danh sach Whitelist");
        }

        hasVoted[msg.sender] = true;
        candidates[_candidateId].voteCount++;

        emit VoteCast(_candidateId);
    }
}

contract ElectionFactory {
    address[] public deployedElections;
    address public factoryOwner;

    event ElectionCreated(address indexed electionAddress, string name, address admin, bool isPrivate);

    constructor() {
        factoryOwner = msg.sender;
    }

    modifier onlyFactoryOwner() {
        require(msg.sender == factoryOwner, "Loi: Chi admin he thong moi duoc tao hom phieu");
        _;
    }

    function createElection(string memory _name, bool _isPrivate) public onlyFactoryOwner {
        Election newElection = new Election(msg.sender, _name, _isPrivate);
        deployedElections.push(address(newElection));
        emit ElectionCreated(address(newElection), _name, msg.sender, _isPrivate);
    }
    
    function getDeployedElections() public view returns (address[] memory) {
        return deployedElections;
    }
}
