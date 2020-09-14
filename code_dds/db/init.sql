USE DeliverySystem;
DROP TABLE IF EXISTS Users;
DROP TABLE IF EXISTS Facilities;
DROP TABLE IF EXISTS Projects;
DROP TABLE IF EXISTS Files;
DROP TABLE IF EXISTS ProjectFiles;

CREATE TABLE Users (
    id CHAR(4),
    first_name VARCHAR(40) NOT NULL,
    last_name VARCHAR(40) NOT NULL,
    username VARCHAR(15) NOT NULL,
    password_ VARCHAR(102) NOT NULL,
    settings VARCHAR(42) NOT NULL,
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    PRIMARY KEY(id),
    UNIQUE(username),
    UNIQUE(email)
);
CREATE TABLE Facilities (
    id CHAR(4),
    name_ VARCHAR(100) NOT NULL,
    internal_ref VARCHAR(10) NOT NULL,
    username VARCHAR(15) NOT NULL,
    password_ VARCHAR(102) NOT NULL,
    settings VARCHAR(42) NOT NULL,
    email VARCHAR(100) NOT NULL,
    PRIMARY KEY(id),
    UNIQUE(internal_ref)
);
CREATE TABLE Projects (
    id CHAR(4),
    title VARCHAR(100) NOT NULL,
    category VARCHAR(40),
    order_date DATE,
    delivery_date DATE,
    status_ VARCHAR(20),
    sensitive_ BOOL NOT NULL,
    description_ TEXT,
    pi_ VARCHAR(50) NOT NULL,
    owner_ CHAR(4) NOT NULL,
    facility CHAR(4) NOT NULL,
    size INT,
    delivery_option VARCHAR(10) NOT NULL,
    public_key VARCHAR(64) NOT NULL,
    private_key VARCHAR(200) NOT NULL,
    nonce VARCHAR(24) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (owner_) REFERENCES Users(id) ON DELETE CASCADE,
    FOREIGN KEY (facility) REFERENCES Facilities(id) ON DELETE CASCADE
);
CREATE TABLE S3Projects (
    id CHAR(10), 
    project_s3 CHAR(4), 
    PRIMARY KEY (id), 
    FOREIGN KEY (project_s3) REFERENCES Projects(id) ON DELETE CASCADE
);
CREATE TABLE Files (
    id INT NOT NULL AUTO_INCREMENT,
    name_ VARCHAR(100) NOT NULL,
    directory_path VARCHAR(500),
    size INT NOT NULL,
    format_ VARCHAR(10),
    compressed BOOL NOT NULL,
    public_key VARCHAR(64) NOT NULL,
    salt VARCHAR(30) NOT NULL,
    date_uploaded DATE,
    PRIMARY KEY(id)
);
CREATE TABLE ProjectFiles (
    id INT NOT NULL AUTO_INCREMENT,
    fileid INT NOT NULL,
    projectid CHAR(4) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (fileid) REFERENCES Files(id) ON DELETE CASCADE,
    FOREIGN KEY (projectid) REFERENCES Projects(id) ON DELETE CASCADE
);
INSERT INTO Facilities (id, name_, internal_ref, username, password_, settings, email) VALUES
    ('fac1', 'National Seq Facility', 'nsf', 'fac1_username', 'fac1_password', 'fac1_settings', 'supprt@nsf.se'),
    ('fac2', 'Proteomics Facility', 'pfc', 'fac2_username', 'fac2_password', 'fac2_settings', 'supprt@pfc.se');
INSERT INTO Users (id, first_name, last_name, username, password_, settings, email, phone) VALUES
    ('0001', 'Ross', 'Geller', 'rossy', 'pbkdf2:sha256:15000', 'settingshere', 'ross.geller@museum.com', '070-000 00 01'),
    ('0002', 'Rachel', 'Green', 'rache', 'pbkdf2:sha256:15000', 'settingshere', 'rachel.green@ralphlauren.com', '070-000 00 02');
    
INSERT INTO Projects (id, title, category, order_date, delivery_date, status_, sensitive_, description_, pi_, owner_, facility, size, delivery_option, public_key, private_key, nonce) VALUES
    ('prj1', 'Whole genome sequencing', 'Genomics', '2019-05-25', '2019-09-02', 'Delivered', True, 'Whole genome sequencing of the spruce genome, that will go published',
     'Andrey Ericsson', '0001', 'fac1', 0, 'S3', 'publickey', 'privatekey', 'nonce'),
    ('prj2', 'Protein modelling', 'Proteomics', '2019-08-05', '2019-10-17', 'Delivered',
      False, 'Modelling of endo protein structure', 'Olof Hoglund', '0002', 'fac2', 
      0, 'S3', 'publickey', 'privatekey', 'nonce');
INSERT INTO S3Projects (id, project_s3) VALUES
    ('s3proj1', 'prj1'), 
    ('s3proj2', 'prj2');     
      
INSERT INTO Projects (id, title, category, order_date, status_, sensitive_, description_, pi_, owner_, facility) VALUES
    ('prj3', 'Virus phage sequencing', 'Genomics', '2019-05-25', 'Ongoing', True,
     'Corono virus sequencing to trap different phages', 'Nemo Svensson', '0001', 'fac1', 
     0, 'S3', 'publickey', 'privatekey', 'nonce');

-- INSERT INTO Files (ID, Name, Size, Format, DateUploaded, Checksum) VALUES
--     (1, 'testfile1.fna ', 109246967, 'fasta', '2019-09-02', '01257ca3d305cff5b11f4abdb0c'),
--     (2, 'testfile2.fna ', 109246967, 'fasta', '2019-09-02', '01257ca3d305cff5b11f4abdb0c'),
--     (3, 'testfile3.fna ', 109246967, 'fasta', '2019-09-02', '01257ca3d305cff5b11f4abdb0c'),
--     (4, 'testfile4.fna ', 109246967, 'fasta', '2019-09-02', '01257ca3d305cff5b11f4abdb0c'),
--     (5, 'testfile5.fna ', 109246967, 'fasta', '2019-10-17', '01257ca3d305cff5b11f4abdb0c'),
--     (6, 'testfile6.fna ', 109246967, 'fasta', '2019-10-17', '01257ca3d305cff5b11f4abdb0c');
-- INSERT INTO ProjectFiles (ID, FileID, ProjectID) VALUES
--     (1, 1, 'prj1'),
--     (2, 2, 'prj1'),
--     (3, 3, 'prj1'),
--     (4, 4, 'prj1'),
--     (5, 5, 'prj2'),
--     (6, 6, 'prj2');
