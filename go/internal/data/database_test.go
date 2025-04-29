package data

import (
	"database/sql"
	"path/filepath"
	"testing"

	"telemetryserver/internal/config"
)

func newTestDatabase(t *testing.T, now *float64, overwrite bool, filename string) (*Database, *DataCache) {
	t.Helper()
	cache := NewDataCache(config.DataKeys)
	db, err := NewDatabase(cache, filename, overwrite)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Shutdown() })
	return db, cache
}

func TestDatabaseSaveRow(t *testing.T) {
	now := fakeClock(t)
	file := filepath.Join(t.TempDir(), "test.db")
	db, cache := newTestDatabase(t, now, true, file)
	db.ResetTimestamp()

	if db.TableName() != config.DbTablePrefix+"0" {
		t.Fatalf("table name = %s", db.TableName())
	}

	cache.Set("batteryVoltage", 36.25)
	cache.Set("motorRpm", 1500)

	*now += 2 // step past the save rate limiter
	if err := db.SaveData(); err != nil {
		t.Fatal(err)
	}

	var timestamp, voltage float64
	var rpm float64
	var gpsFix sql.NullFloat64
	row := db.db.QueryRow("select timestamp, batteryVoltage, motorRpm, gpsFix from dataSession0")
	if err := row.Scan(&timestamp, &voltage, &rpm, &gpsFix); err != nil {
		t.Fatal(err)
	}
	if timestamp != 2 {
		t.Fatalf("timestamp = %v, want 2 (relative to ResetTimestamp)", timestamp)
	}
	if voltage != 36.25 || rpm != 1500 {
		t.Fatalf("saved values wrong: voltage=%v rpm=%v", voltage, rpm)
	}
	if gpsFix.Valid {
		t.Fatal("unset data point must be saved as NULL")
	}

	// Second save within the rate limit is a no-op.
	if err := db.SaveData(); err != nil {
		t.Fatal(err)
	}
	var count int
	if err := db.db.QueryRow("select count(*) from dataSession0").Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 1 {
		t.Fatalf("row count = %d, want 1 (rate limited)", count)
	}
}

func TestDatabaseSessionMetadata(t *testing.T) {
	now := fakeClock(t)
	file := filepath.Join(t.TempDir(), "test.db")
	db, _ := newTestDatabase(t, now, true, file)

	var session string
	if err := db.db.QueryRow("select session from sessionMetadata").Scan(&session); err != nil {
		t.Fatal(err)
	}
	if session != "dataSession0" {
		t.Fatalf("session metadata = %s", session)
	}

	if err := db.IncrementSessionID(); err != nil {
		t.Fatal(err)
	}
	if db.TableName() != "dataSession1" {
		t.Fatalf("table after increment = %s", db.TableName())
	}
	var count int
	if err := db.db.QueryRow("select count(*) from sessionMetadata").Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 2 {
		t.Fatalf("sessionMetadata rows = %d, want 2", count)
	}
}

func TestDatabasePreserveSessionsWithoutOverwrite(t *testing.T) {
	now := fakeClock(t)
	file := filepath.Join(t.TempDir(), "test.db")

	db1, _ := newTestDatabase(t, now, false, file)
	if db1.GetSessionID() != 0 {
		t.Fatalf("first session id = %d", db1.GetSessionID())
	}
	db1.Shutdown()

	// Reopening without overwrite must pick the next free session id.
	db2, _ := newTestDatabase(t, now, false, file)
	if db2.GetSessionID() != 1 {
		t.Fatalf("second session id = %d, want 1", db2.GetSessionID())
	}
	if !db2.contains("dataSession0") {
		t.Fatal("previous session should still exist")
	}
}

func TestDatabaseOverwriteErasesSessions(t *testing.T) {
	now := fakeClock(t)
	file := filepath.Join(t.TempDir(), "test.db")

	db1, _ := newTestDatabase(t, now, false, file)
	db1.Shutdown()

	db2, _ := newTestDatabase(t, now, true, file)
	if db2.GetSessionID() != 0 {
		t.Fatalf("session id after overwrite = %d, want 0", db2.GetSessionID())
	}
	if db2.contains("dataSession1") {
		t.Fatal("old sessions should have been dropped")
	}
}

func TestDatabaseClearData(t *testing.T) {
	now := fakeClock(t)
	file := filepath.Join(t.TempDir(), "test.db")
	db, cache := newTestDatabase(t, now, true, file)
	cache.Set("batteryVoltage", 36)
	*now += 2
	if err := db.SaveData(); err != nil {
		t.Fatal(err)
	}
	if err := db.ClearData(); err != nil {
		t.Fatal(err)
	}
	var count int
	if err := db.db.QueryRow("select count(*) from dataSession0").Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 0 {
		t.Fatalf("rows after clear = %d", count)
	}
}
