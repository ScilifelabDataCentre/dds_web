<?php

$servername = "localhost";
$username = "root";
$password = "root";
$db = "dp_database";

$conn = new mysqli ($servername, $username, $password, $db);

if (mysqli_connect_error()) {
    die("Connect Error (" . mysqli_connect_errno() .') '
    . mysqli_connect_error());
}
else {

}



?>