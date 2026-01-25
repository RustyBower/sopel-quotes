# sopel-quotes

A Sopel IRC bot plugin for handling user added quotes with MySQL storage.

> **Note:** This package was previously published as `sopel-modules.quotes`.
> Please update your dependencies to use `sopel-quotes` instead.

## Installation

```bash
pip install sopel-quotes
```

### System Requirements

```bash
# Debian/Ubuntu
apt-get install libmysqlclient-dev
```

## Configuration

```ini
[quotes]
db_host = localhost
db_user = quotes
db_pass = your_password
db_name = quotes
```

## Usage

### Adding a Quote

```
.quote <key> = <value>
.quoteadd <key> = <value>
```

### Retrieving a Quote

```
.quote           # Random quote
.quote <key>     # Specific quote
```

### Searching Quotes

```
.match <pattern>  # Search for keys matching pattern
```

### Deleting a Quote

```
.quotedel <key>
.quotedelete <key>
```

## Requirements

- Sopel 8.0+
- Python 3.8+
- MySQL/MariaDB database

## License

MIT License
