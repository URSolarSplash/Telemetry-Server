package data

import (
	"database/sql"
	"fmt"
	"sort"
	"strings"

	"telemetryserver/internal/config"
	"telemetryserver/internal/stats"

	_ "modernc.org/sqlite" // pure-Go SQLite driver, keeps the binary static
)

// Database is responsible for storage of the data cache to the sqlite database.
type Database struct {
	cache            *DataCache
	filename         string
	overwriteOnStart bool
	timestampOffset  float64
	lastSave         float64
	db               *sql.DB
	sessionList      []string
	sessionID        int
	tableName        string
}

// NewDatabase opens (creating if needed) the sqlite file and prepares the
// session table, mirroring Python's Database.__init__.
func NewDatabase(cache *DataCache, filename string, overwrite bool) (*Database, error) {
	db, err := sql.Open("sqlite", filename)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}
	// The main loop and shutdown path are single-goroutine; a single
	// connection also avoids SQLITE_BUSY between them.
	db.SetMaxOpenConns(1)
	d := &Database{
		cache:            cache,
		filename:         filename,
		overwriteOnStart: overwrite,
		lastSave:         Now(),
		db:               db,
	}
	if err := d.getSessions(); err != nil {
		db.Close()
		return nil, err
	}
	// Auto set the session id to one past the existing session
	for d.contains(config.DbTablePrefix + fmt.Sprint(d.sessionID)) {
		d.sessionID++
	}
	if err := d.setSchema(); err != nil {
		db.Close()
		return nil, err
	}
	return d, nil
}

func (d *Database) contains(table string) bool {
	for _, t := range d.sessionList {
		if t == table {
			return true
		}
	}
	return false
}

// getSessions refreshes the list of sessions (tables) in the database.
func (d *Database) getSessions() error {
	rows, err := d.db.Query("select name from sqlite_master WHERE type='table';")
	if err != nil {
		return fmt.Errorf("list sessions: %w", err)
	}
	defer rows.Close()
	d.sessionList = nil
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			return err
		}
		d.sessionList = append(d.sessionList, name)
	}
	return rows.Err()
}

// ResetTimestamp makes saved timestamps relative to now instead of the epoch.
func (d *Database) ResetTimestamp() {
	d.timestampOffset = Now()
}

// Shutdown closes the database file.
func (d *Database) Shutdown() error {
	return d.db.Close()
}

// GetSessionID returns the current session id.
func (d *Database) GetSessionID() int {
	return d.sessionID
}

// TableName returns the active session table name.
func (d *Database) TableName() string {
	return d.tableName
}

// IncrementSessionID moves to the next session and creates its table.
func (d *Database) IncrementSessionID() error {
	d.sessionID++
	return d.createSessionTable()
}

// SetSessionID selects a specific session id and creates its table.
func (d *Database) SetSessionID(id int) error {
	d.sessionID = id
	return d.createSessionTable()
}

// SaveData saves a row of data into the database, rate limited to config.SaveRate.
func (d *Database) SaveData() error {
	if Now()-d.lastSave < config.SaveRate {
		return nil
	}
	d.lastSave = Now()

	keys := d.cache.GetKeys()
	fields := ""
	valuePlaceholders := ""
	valueList := make([]any, 0, len(keys)+1)
	timestamp := Now() - d.timestampOffset
	valueList = append(valueList, timestamp)
	for _, key := range keys {
		fields += "," + key
		valuePlaceholders += ",?"
		if v, ok := d.cache.Get(key); ok {
			valueList = append(valueList, v)
		} else {
			valueList = append(valueList, nil)
		}
	}
	sqlQuery := "insert into " + d.tableName + "(timestamp" + fields + ") values (?" + valuePlaceholders + ")"
	if _, err := d.db.Exec(sqlQuery, valueList...); err != nil {
		return fmt.Errorf("save data row: %w", err)
	}
	return nil
}

// ClearData removes all data from the current session.
func (d *Database) ClearData() error {
	_, err := d.db.Exec("delete from " + d.tableName + ";")
	return err
}

// createSessionTable creates a session table for the current session id, if it
// doesn't exist, and records the session in sessionMetadata.
func (d *Database) createSessionTable() error {
	if _, err := d.db.Exec(`create table if not exists sessionMetadata(session TEXT PRIMARY KEY, created TEXT, UNIQUE(session))`); err != nil {
		return fmt.Errorf("create sessionMetadata: %w", err)
	}

	d.tableName = config.DbTablePrefix + fmt.Sprint(d.sessionID)
	keys := d.cache.GetKeys()
	sorted := append([]string(nil), keys...)
	sort.Strings(sorted)
	var tableFields strings.Builder
	tableFields.WriteString("id INTEGER PRIMARY KEY, timestamp NUMERIC")
	for _, key := range sorted {
		fmt.Fprintf(&tableFields, ", %s NUMERIC", key)
	}
	if _, err := d.db.Exec("create table if not exists " + d.tableName + "(" + tableFields.String() + ")"); err != nil {
		return fmt.Errorf("create session table: %w", err)
	}

	// Insert a timestamp into session metadata for when this session was created
	if _, err := d.db.Exec("insert or ignore into sessionMetadata(session, created) values(?,datetime('now'))", d.tableName); err != nil {
		return fmt.Errorf("insert session metadata: %w", err)
	}

	if err := d.getSessions(); err != nil {
		return err
	}
	fmt.Println("[Database] Current session name: " + d.tableName)

	stats.SetActiveSession(d.tableName)
	return nil
}

// setSchema optionally erases previous sessions and creates the session table.
func (d *Database) setSchema() error {
	if d.overwriteOnStart {
		fmt.Println("[Database] Overwriting previous sessions...")
		for _, table := range d.sessionList {
			if _, err := d.db.Exec("drop table if exists " + table + ";"); err != nil {
				return fmt.Errorf("drop table %s: %w", table, err)
			}
		}
		if _, err := d.db.Exec("drop table if exists sessionMetadata;"); err != nil {
			return err
		}
		d.sessionID = 0
	}
	return d.createSessionTable()
}
