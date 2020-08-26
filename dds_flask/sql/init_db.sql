USE DeliverySystem;
CREATE TABLE Users (
    ID CHAR(4),
    Firstname VARCHAR(40) NOT NULL,
    Lastname VARCHAR(40) NOT NULL,
    Username VARCHAR(15) NOT NULL,
    Password VARCHAR(25) NOT NULL,
    Email VARCHAR(100) NOT NULL,
    PRIMARY KEY(ID),
    UNIQUE(Username),
    UNIQUE(Email)
);
CREATE TABLE Facilities (
    ID CHAR(4),
    Name VARCHAR(100) NOT NULL,
    InternalRef VARCHAR(10) NOT NULL,
    Email VARCHAR(100) NOT NULL,
    PRIMARY KEY(ID),
    UNIQUE(InternalRef)
);
CREATE TABLE Projects (
    ID CHAR(4),
    Title VARCHAR(100) NOT NULL,
    Category VARCHAR(40),
    OrderDate DATE,
    DeliveryDate DATE,
    Status VARCHAR(20),
    Sensitivity BOOL NOT NULL,
    Description TEXT,
    PI VARCHAR(50) NOT NULL,
    Owner CHAR(4) NOT NULL,
    Facility CHAR(4) NOT NULL,
    PRIMARY KEY (ID),
    FOREIGN KEY (Owner) REFERENCES Users(ID) ON DELETE CASCADE,
    FOREIGN KEY (Facility) REFERENCES Facilities(ID) ON DELETE CASCADE
);
CREATE TABLE Files (
    ID INT NOT NULL AUTO_INCREMENT,
    Name VARCHAR(100) NOT NULL,
    Size INT NOT NULL,
    Format VARCHAR(10),
    DateUploaded DATE,
    Checksum VARCHAR(100) NOT NULL,
    PRIMARY KEY(ID)
);
CREATE TABLE ProjectFiles (
    ID INT NOT NULL AUTO_INCREMENT,
    FileID INT NOT NULL,
    ProjectID CHAR(4) NOT NULL,
    PRIMARY KEY (ID),
    FOREIGN KEY (FileID) REFERENCES Files(ID) ON DELETE CASCADE,
    FOREIGN KEY (ProjectID) REFERENCES Projects(ID) ON DELETE CASCADE
);
INSERT INTO Facilities (ID, Name, InternalRef, Email) VALUES
    ('fac1', 'National Seq Facility', 'nsf', 'supprt@nsf.se'),
    ('fac2', 'Proteomics Facility', 'pfc', 'supprt@pfc.se');
INSERT INTO Users (ID, Firstname, Lastname, Username, Password, Email) VALUES
    ('usr1', 'Ross', 'Gellar', 'rossy', 'rosspass', 'ross.gellar@museum.com'),
    ('usr2', 'Racheal', 'Green', 'rache', 'rachpass', 'racheal.green@ralphlauren.com');
    
INSERT INTO Projects (ID, Title, Category, OrderDate, DeliveryDate, Status, Sensitivity, Description, PI, Owner, Facility) VALUES
    ('prj1', 'Whole genome sequencing', 'Genomics', '2019-05-25', '2019-09-02', 'Delivered',
      True, 'Whole genome sequencing of the spruce genome, that will go published',
     'Andrey Ercisson', 'usr1', 'fac1'),
    ('prj2', 'Protein modelling', 'Proteomics', '2019-08-05', '2019-10-17', 'Delivered',
      False, 'Modelling of endo protein structure', 'Olof Hoglund', 'usr2', 'fac2');
      
      
INSERT INTO Projects (ID, Title, Category, OrderDate, Status, Sensitivity, Description, PI, Owner, Facility) VALUES
    ('prj3', 'Virus phage sequencing', 'Genomics', '2019-05-25', 'Ongoing', True,
     'Corono virus sequencing to trap different phages', 'Nemo Svensson', 'usr1', 'fac1');
INSERT INTO Files (ID, Name, Size, Format, DateUploaded, Checksum) VALUES
    (1, 'testfile1.fna ', 109246967, 'fasta', '2019-09-02', '01257ca3d305cff5b11f4abdb0c'),
    (2, 'testfile2.fna ', 109246967, 'fasta', '2019-09-02', '01257ca3d305cff5b11f4abdb0c'),
    (3, 'testfile3.fna ', 109246967, 'fasta', '2019-09-02', '01257ca3d305cff5b11f4abdb0c'),
    (4, 'testfile4.fna ', 109246967, 'fasta', '2019-09-02', '01257ca3d305cff5b11f4abdb0c'),
    (5, 'testfile5.fna ', 109246967, 'fasta', '2019-10-17', '01257ca3d305cff5b11f4abdb0c'),
    (6, 'testfile6.fna ', 109246967, 'fasta', '2019-10-17', '01257ca3d305cff5b11f4abdb0c');
INSERT INTO ProjectFiles (ID, FileID, ProjectID) VALUES
    (1, 1, 'prj1'),
    (2, 2, 'prj1'),
    (3, 3, 'prj1'),
    (4, 4, 'prj1'),
    (5, 5, 'prj2'),
    (6, 6, 'prj2');
