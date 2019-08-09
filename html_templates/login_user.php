<html>
<body>
<?php
$host = "localhost";
$username = "ina";
$password = "inainaina";
$database = "inas_db";

// Create connection
$conn = mysqli_connect($host, $username, $password, $database);

if (mysqli_connect_errno()) {
    echo "Failed to connect to MySQL: (" . mysqli_connect_error();
}
else {
    $command = "INSERT INTO inas_db.INA(`name`, `random`) VALUES ('John', '29')";
    if (mysqli_query($conn, $command)) {
        echo "New record created!";
    }
    else {
        echo "Error: " . mysqli_error($conn);
    }
}

mysqli_close($conn);
?>
</body>
</html>