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
    sensitive_ TINYINT(1) NOT NULL,
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
    compressed TINYINT(1) NOT NULL,
    public_key VARCHAR(64) NOT NULL,
    salt VARCHAR(50) NOT NULL,
    date_uploaded DATETIME NOT NULL DEFAULT NOW(),
    project_id CHAR(4) NOT NULL,
    PRIMARY KEY(id), 
    FOREIGN KEY(project_id) REFERENCES Projects(id)
);

DELIMITER $$

CREATE TRIGGER project_size_insert 
AFTER INSERT ON Files 
FOR EACH ROW 
BEGIN      
    DECLARE tot_size INT;    

    SELECT SUM(size) INTO tot_size
    FROM Files WHERE project_id=new.project_id; 
    
    UPDATE Projects 
    SET size = tot_size 
    WHERE Projects.id=new.project_id;  
END$$

CREATE TRIGGER project_size_update
AFTER UPDATE ON Files 
FOR EACH ROW 
BEGIN      
    DECLARE tot_size INT;    

    SELECT SUM(size) INTO tot_size
    FROM Files WHERE project_id=new.project_id; 
    
    UPDATE Projects 
    SET size = tot_size 
    WHERE Projects.id=new.project_id;  
END$$

CREATE TRIGGER project_size_delete
AFTER DELETE ON Files 
FOR EACH ROW 
BEGIN      
    DECLARE tot_size INT;    

    SELECT SUM(size) INTO tot_size
    FROM Files WHERE project_id=old.project_id; 
    
    UPDATE Projects 
    SET size = tot_size 
    WHERE Projects.id=old.project_id;  
END$$

DELIMITER ;

INSERT INTO Facilities (id, name_, internal_ref, username, password_, settings, email) VALUES
    ('fac1', 'National Seq Facility', 'nsf', 'fac1_username', 'fac1_password', 'fac1_settings', 'supprt@nsf.se'),
    ('fac2', 'Proteomics Facility', 'pfc', 'fac2_username', 'fac2_password', 'fac2_settings', 'supprt@pfc.se');
INSERT INTO Users (id, first_name, last_name, username, password_, settings, email, phone) VALUES
    ('0001', 'Ross', 'Geller', 'rossy', 'pbkdf2:sha256:15000', 'settingshere', 'ross.geller@museum.com', '070-000 00 01'),
    ('0002', 'Rachel', 'Green', 'rache', 'pbkdf2:sha256:15000', 'settingshere', 'rachel.green@ralphlauren.com', '070-000 00 02');
    
INSERT INTO Projects (id, title, category, order_date, delivery_date, status_, sensitive_, description_, pi_, owner_, facility, size, delivery_option, public_key, private_key, nonce) VALUES
    ('prj1', 'Whole genome sequencing', 'Genomics', '2019-05-25', '2019-09-02', 'Delivered', 
    True, 'Whole genome sequencing of the spruce genome, that will go published',
     'Andrey Ericsson', '0001', 'fac1', 0, 'S3', "8F88EAA7B72DB95BE36D6B1EA83064C3F5F8B5306ACB7457B1E49659FF60142C", 'privatekey', 'nonce'),
    ('prj2', 'Protein modelling', 'Proteomics', '2019-08-05', '2019-10-17', 'Delivered',
      False, 'Modelling of endo protein structure', 'Olof Hoglund', '0002', 'fac2', 
      0, 'S3', 'publickey', 'privatekey', 'nonce'), 
    ('prj3', 'Virus phage sequencing', 'Genomics', '2019-05-25', '2019-07-29', 'Ongoing', 
    True, 'Corono virus sequencing to trap different phages', 'Nemo Svensson', '0001', 'fac1', 
    0, 'S3', 'publickey', 'privatekey', 'nonce');

INSERT INTO S3Projects (id, project_s3) VALUES
    ('s3proj1', 'prj1'), 
    ('s3proj2', 'prj2');     
      
INSERT INTO Files (id, name_, directory_path, size, format_, compressed, public_key, salt, date_uploaded, project_id) VALUES
    (1, 'testfile1.fna', '', 109246967, 'fasta', 1, 'file_public', 'file_salt', '2019-09-02', 'prj1'),
    (2, 'testfile2.fna', '', 109246967, 'fasta', 0, 'file_public', 'file_salt', '2019-09-02', 'prj1'),
    (3, 'testfile3.fna', '', 109246967, 'fasta', 1, 'file_public', 'file_salt', '2019-09-02', 'prj1'),
    (4, 'testfile4.fna', '', 109246967, 'fasta', 0, 'file_public', 'file_salt', '2019-09-02', 'prj1'),
    (5, 'testfile5.fna', '', 109246967, 'fasta', 1, 'file_public', 'file_salt', '2019-10-17', 'prj2'),
    (6, 'testfile6.fna', '', 109246967, 'fasta', 0, 'file_public', 'file_salt', '2019-10-17', 'prj2');