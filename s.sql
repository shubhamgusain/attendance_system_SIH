CREATE TABLE face_images (
    id INT NOT NULL AUTO_INCREMENT,
    class_name VARCHAR(100),
    roll_no VARCHAR(20),
    image_data LONGBLOB,
    PRIMARY KEY (id)
);
