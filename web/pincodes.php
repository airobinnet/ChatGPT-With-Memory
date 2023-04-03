<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_POST['username']) && isset($_POST['pincode'])) {
        $username = $_POST['username'];
        $pincode = $_POST['pincode'];

        $db = new SQLite3('pincodes.db');

        // Create the table if it doesn't exist
        $db->exec('CREATE TABLE IF NOT EXISTS pincodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            pincode TEXT NOT NULL
        );');

        $stmt = $db->prepare('SELECT pincode FROM pincodes WHERE username = :username');
        $stmt->bindValue(':username', $username, SQLITE3_TEXT);
        $result = $stmt->execute();
        $row = $result->fetchArray(SQLITE3_ASSOC);

        if ($row === false) {
            $stmt = $db->prepare('INSERT INTO pincodes (username, pincode) VALUES (:username, :pincode)');
            $stmt->bindValue(':username', $username, SQLITE3_TEXT);
            $stmt->bindValue(':pincode', $pincode, SQLITE3_TEXT);
            $stmt->execute();
            echo 'success';
        } else {
            if ($row['pincode'] === $pincode) {
                echo 'success';
            } else {
                echo 'failure';
            }
        }
    }
}
?>
