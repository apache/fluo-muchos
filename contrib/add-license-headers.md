## Adding licence header to Muchos files

Using [license-maven-plugin][license-plugin] we can generate a consistent license
header for the project with the following command.

* Temporally convert the project to a maven project. Make sure not to commit the new `pom.xml` file.
* Via command line, run the following command to generate the license header.

```sh
mvn com.mycila:license-maven-plugin:3.0:format -Dlicense.header=contrib/license-header.txt
```

* Check the output for warnings and manually add the appropriate license to those files.

[license-plugin]: https://code.mycila.com/license-maven-plugin/
