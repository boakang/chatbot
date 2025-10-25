-- Copyright (c) Microsoft Corporation. All rights reserved.
-- Licensed under the MIT License.

-- Bảng lưu thông tin nhân viên
CREATE TABLE Employees (
    EmployeeID NVARCHAR(50) PRIMARY KEY,
    EmployeeName NVARCHAR(200) NOT NULL,
    CreatedAt DATETIME DEFAULT GETDATE()
);

-- Bảng lưu admin keys
CREATE TABLE AdminKeys (
    KeyID INT IDENTITY(1,1) PRIMARY KEY,
    AdminKey NVARCHAR(100) UNIQUE NOT NULL,
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME DEFAULT GETDATE()
);

-- Bảng lưu tickets
CREATE TABLE Tickets (
    TicketID INT IDENTITY(1,1) PRIMARY KEY,
    EmployeeID NVARCHAR(50) NOT NULL,
    TicketContent NVARCHAR(MAX) NOT NULL,
    Status NVARCHAR(50) DEFAULT 'Pending', -- Pending, Approved, Rejected
    CreatedAt DATETIME DEFAULT GETDATE(),
    UpdatedAt DATETIME DEFAULT GETDATE(),
    ApprovedBy NVARCHAR(50) NULL,
    FOREIGN KEY (EmployeeID) REFERENCES Employees(EmployeeID)
);

-- Insert dữ liệu mẫu
INSERT INTO AdminKeys (AdminKey) VALUES ('123222');

INSERT INTO Employees (EmployeeID, EmployeeName) VALUES 
('NV001', N'Nguyễn Văn A'),
('NV002', N'Trần Thị B'),
('NV003', N'Lê Văn C');

-- Insert tickets mẫu
INSERT INTO Tickets (EmployeeID, TicketContent, Status) VALUES 
('NV001', N'Yêu cầu nghỉ phép ngày 30/10/2025', 'Pending'),
('NV002', N'Đề xuất tăng lương', 'Pending'),
('NV003', N'Yêu cầu đổi ca làm việc', 'Approved');